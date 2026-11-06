"""Opt-in synthetic 300 MB benchmark for the isolated PR93 query pipeline.

Run from a checkout: python scripts/benchmark_pr93_queries.py --run
Uses less than 2 GB of temporary files and requires over 3 GB free in /tmp.
Standard-library only; no network, credentials or production routes are used.
/tmp may be memory-backed: these timings do not establish durable-disk throughput.
"""
import gc
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import time
import tracemalloc
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.experimental_ingest import spool, index_csv
from server.experimental_query import page, summarize

TARGET = 300_000_000
ROWS = 50_000
WIDTH = 607
CEILING = 2_000_000_000
HUGE = 10 ** 50 + 12345
selected = ['c500', 'c2', 'c0', 'c606', 'c1']


def run_benchmark():
    usage = shutil.disk_usage('/tmp')
    assert usage.free > CEILING + 1_000_000_000, 'Insufficient temporary disk headroom'
    report = {'source_bytes': TARGET, 'rows': ROWS, 'columns': WIDTH,
              'selected_columns': selected, 'spool_chunk_bytes': 65_536,
              'free_temp_bytes_before': usage.free, 'wall_seconds': {}}
    peak_disk = 0


    def emit(stage, **values):
        print(json.dumps({'stage': stage, **values}), flush=True)


    def check_disk(root):
        nonlocal peak_disk
        size = sum(p.stat().st_size for p in root.iterdir() if p.is_file())
        peak_disk = max(peak_disk, size)
        assert size < CEILING, 'Temporary data ceiling exceeded'
        assert shutil.disk_usage(root).free > 1_000_000_000, 'Temporary disk headroom exhausted'
        return size


    def decimal_text(coefficient, places):
        sign = '-' if coefficient < 0 else ''
        whole, fractional = divmod(abs(coefficient), 10 ** places)
        return sign + str(whole) + '.' + str(fractional).zfill(places)


    def oracle_text(value):
        # Independent Fraction/long-division oracle, not the query's accumulator.
        value = Fraction(value)
        sign = '-' if value < 0 else ''
        whole, remainder = divmod(abs(value.numerator), value.denominator)
        decimals = []
        while remainder:
            digit, remainder = divmod(remainder * 10, value.denominator)
            decimals.append(str(digit))
        return sign + str(whole) + ('.' + ''.join(decimals) if decimals else '')


    def expected_record(ordinal):
        amount = (HUGE * 1000 + ordinal % 1000) * (-1 if ordinal % 2 else 1)
        return [str(ordinal % 7), decimal_text(amount, 3), str(ordinal), None,
                decimal_text(ordinal % 2001 - 1000, 2)]


    def assert_page(result, first, last):
        assert result['columns'] == selected
        assert [r['ordinal'] for r in result['rows']] == list(range(first, last + 1))
        for record in result['rows']:
            expected = expected_record(record['ordinal'])
            values = record['values']
            assert [values[i] for i in (0, 1, 2, 4)] == [expected[i] for i in (0, 1, 2, 4)]
            assert values[3].startswith('f') and set(values[3][1:]) <= {'x'}
        assert result['next'] == last


    root_path = None
    try:
        with tempfile.TemporaryDirectory(prefix='pr93-synthetic-300mb-', dir='/tmp') as directory:
            root = Path(directory)
            root_path = root
            source, staged, database = root/'source.csv', root/'staged.csv', root/'index.sqlite'
            start = time.perf_counter()
            header = (','.join(f'c{i}' for i in range(WIDTH)) + '\n').encode('ascii')
            base_row_bytes, remainder = divmod(TARGET - len(header), ROWS)
            digest = hashlib.sha256()
            max_field_bytes = max_record_bytes = 0
            with source.open('wb') as stream:
                stream.write(header)
                digest.update(header)
                for ordinal in range(1, ROWS + 1):
                    projected = expected_record(ordinal)
                    fields = ['syn00001'] * WIDTH
                    fields[0], fields[1], fields[2], fields[500], fields[606] = (
                        projected[2], projected[4], projected[1], projected[0], 'f')
                    target_row_bytes = base_row_bytes + (remainder if ordinal == ROWS else 0)
                    baseline = ','.join(fields) + '\n'
                    padding = target_row_bytes - len(baseline)
                    assert 0 <= padding < 65_535
                    fields[606] += 'x' * padding
                    record = (','.join(fields) + '\n').encode('ascii')
                    assert len(record) == target_row_bytes
                    max_field_bytes = max(max_field_bytes, len(fields[606]))
                    max_record_bytes = max(max_record_bytes, len(record))
                    stream.write(record)
                    digest.update(record)
            report['wall_seconds']['generate'] = round(time.perf_counter() - start, 6)
            assert source.stat().st_size == TARGET
            source_sha = digest.hexdigest()
            report['max_csv_field_bytes'] = max_field_bytes
            report['max_csv_record_bytes'] = max_record_bytes
            emit('generated', seconds=report['wall_seconds']['generate'], source_bytes=source.stat().st_size,
                 max_field_bytes=max_field_bytes, temporary_bytes=check_disk(root))

            def chunks():
                with source.open('rb') as stream:
                    while chunk := stream.read(65_536):
                        yield chunk
            start = time.perf_counter()
            spooled = spool(chunks(), staged)
            report['wall_seconds']['spool'] = round(time.perf_counter() - start, 6)
            assert spooled == {'bytes': TARGET, 'sha256': source_sha}
            assert staged.stat().st_size == TARGET
            # Independent post-write streamed hash verifies the actual staged file.
            start = time.perf_counter()
            with staged.open('rb') as stream:
                staged_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            report['wall_seconds']['verify_staged_hash'] = round(time.perf_counter() - start, 6)
            assert staged_sha == source_sha
            report['sha256'] = source_sha
            emit('spooled', seconds=report['wall_seconds']['spool'], bytes=spooled['bytes'],
                 hash_match=True, temporary_bytes=check_disk(root))

            start = time.perf_counter()
            indexed = index_csv(staged, database, batch_size=500)
            report['wall_seconds']['index'] = round(time.perf_counter() - start, 6)
            assert indexed == {'rows': ROWS, 'columns': WIDTH}
            report['sqlite_bytes'] = database.stat().st_size
            emit('indexed', seconds=report['wall_seconds']['index'], rows=indexed['rows'], columns=indexed['columns'],
                 sqlite_bytes=report['sqlite_bytes'], temporary_bytes=check_disk(root))

            start = time.perf_counter()
            first = page(database, columns=selected, size=7)
            assert_page(first, 1, 7)
            second = page(database, columns=selected, after=first['next'], size=7)
            assert_page(second, 8, 14)
            boundary = page(database, columns=selected, after=ROWS - 3, size=7)
            assert_page(boundary, ROWS - 2, ROWS)
            empty = page(database, columns=selected, after=boundary['next'], size=7)
            assert empty == {'columns': selected, 'rows': [], 'next': None}
            report['wall_seconds']['projected_pages_and_verify'] = round(time.perf_counter() - start, 6)
            report['page_boundary_checks'] = 'ordinals 1-7, 8-14, 49998-50000, then empty'
            emit('projection_verified', seconds=report['wall_seconds']['projected_pages_and_verify'],
                 caller_order=True, page_boundaries=True, temporary_bytes=check_disk(root))
            del first, second, boundary, empty

            # Ground truth derives from arithmetic-series identities, not parsing the CSV.
            cent_cycles, cent_remainder = divmod(ROWS, 2001)
            cent_sum = cent_remainder * (cent_remainder + 1) // 2 - 1000 * cent_remainder
            bucket_cycles, bucket_remainder = divmod(ROWS, 7)
            bucket_sum = bucket_cycles * 21 + bucket_remainder * (bucket_remainder + 1) // 2
            # Each 1,000-row block has cancelling huge signed parts and net -500/1000.
            assert ROWS % 1000 == 0
            expected = {
                'c500': (Fraction(bucket_sum), Fraction(0), Fraction(6)),
                'c2': (Fraction(-500 * (ROWS // 1000), 1000), Fraction(-HUGE * 1000 - 999, 1000),
                       Fraction(HUGE * 1000 + 998, 1000)),
                'c0': (Fraction(ROWS * (ROWS + 1), 2), Fraction(1), Fraction(ROWS)),
                'c1': (Fraction(cent_sum, 100), Fraction(-10), Fraction(10)),
            }
            gc.collect()
            tracemalloc.start()
            start = time.perf_counter()
            result = summarize(database, columns=selected)
            report['wall_seconds']['summarize_with_tracemalloc'] = round(time.perf_counter() - start, 6)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            report['summarize_python_tracemalloc_peak_bytes'] = peak
            assert result['rows_scanned'] == ROWS
            assert list(result['columns']) == selected
            for name, numbers in expected.items():
                assert result['columns'][name] == {
                    'numeric': ROWS, 'blank': 0, 'invalid': 0,
                    'sum': oracle_text(numbers[0]), 'min': oracle_text(numbers[1]), 'max': oracle_text(numbers[2])
                }, 'Independent numeric oracle mismatch'
            assert result['columns']['c606'] == {
                'numeric': 0, 'blank': 0, 'invalid': ROWS, 'sum': None, 'min': None, 'max': None
            }
            report['summary'] = result
            report['temporary_peak_observed_bytes'] = check_disk(root)
            report['temporary_peak_observed_bytes'] = peak_disk
            report['all_checks_passed'] = True
            emit('summary_verified', seconds=report['wall_seconds']['summarize_with_tracemalloc'],
                 rows=result['rows_scanned'], independent_oracle_match=True, python_tracemalloc_peak_bytes=peak,
                 temporary_bytes=check_disk(root))
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        report['temporary_directory_removed'] = root_path is not None and not root_path.exists()
        report['free_temp_bytes_after'] = shutil.disk_usage('/tmp').free
        print('FINAL_AGGREGATE ' + json.dumps(report, sort_keys=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Generate and validate the 300 MB synthetic fixture')
    args = parser.parse_args()
    if not args.run:
        parser.error('Pass --run to opt in to generating up to 2 GB of temporary files')
    run_benchmark()
