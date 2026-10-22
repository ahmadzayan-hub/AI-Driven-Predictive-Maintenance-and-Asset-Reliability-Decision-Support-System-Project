
(()=>{
const $=id=>document.getElementById(id),el={lang:$('lang'),format:$('format'),headline:$('headline'),detail:$('detail'),cta:$('cta'),narration:$('narration'),duration:$('duration'),play:$('play'),stop:$('stop'),record:$('record'),save:$('save'),load:$('load'),project:$('project'),seek:$('seek'),clock:$('clock'),status:$('status'),canvas:$('screen'),audio:$('audio')};
const ctx=el.canvas.getContext('2d');let position=0,playing=false,recording=false,start=0,raf=0,streamURL=null,recorder=null,audioCtx=null,audioNode=null,audioDest=null;
let sourceManifest=null;

function validMotion(data){
  if(!data||data.schema!=='motion-evidence-v1'||!['ar','en'].includes(data.language)
    ||!['wide','vertical'].includes(data.format)||!['SYNTHETIC','INTERNAL'].includes(data.classification)
    ||!Array.isArray(data.scenes)||data.scenes.length!==3
    ||!Number.isFinite(data.duration)||data.duration<3||data.duration>180)throw Error('Invalid evidence storyboard');
  for(let i=0;i<3;i++){
    const scene=data.scenes[i];
    if(scene.kind!==['hook','evidence','action'][i]||typeof scene.text!=='string'||!scene.text.trim()
      ||scene.text.length>480||!Array.isArray(scene.evidence)||!scene.evidence.length)
      throw Error('Invalid scene or missing evidence');
    for(const ref of scene.evidence){
      for(const field of ['source_id','revision','locator']){
        if(typeof ref[field]!=='string'||!/^[-.a-zA-Z0-9_:/#@]{1,150}$/.test(ref[field]))throw Error('Invalid source reference');
      }
      if(!['VERIFIED','RECORDED_IN_REGISTER','SYNTHETIC'].includes(ref.data_status)
        ||(data.classification==='INTERNAL'&&ref.data_status==='SYNTHETIC'))
        throw Error('Unreliable evidence cannot be used for internal source-grounded video');
    }
  }
  return true;
}
function openEvidence(m){
  validMotion(m);
  stop();sourceManifest=m;el.lang.value=m.language;el.format.value=m.format;
  el.headline.value=m.scenes[0].text;el.detail.value=m.scenes[1].text;
  el.cta.value=m.scenes[2].text;el.duration.value=String(m.duration);
  position=0;dims();clock();setStatus('Source-linked storyboard loaded. Text edits require new human fact-check. Never published automatically.');
}
function motionManifest(){
  if(!sourceManifest)throw Error('Import an authorized source-linked storyboard first');
  const sceneTexts=[el.headline.value,el.detail.value,el.cta.value];
  const m={...sourceManifest,language:el.lang.value,format:el.format.value,duration:seconds(),
    approval:{state:'DRAFT',issued:false},
    scenes:sourceManifest.scenes.map((scene,i)=>({...scene,text:sceneTexts[i]}))};
  validMotion(m);return m;
}

const seconds=()=>el.audio.src&&Number.isFinite(el.audio.duration)&&el.audio.duration>0?el.audio.duration:Math.max(3,Math.min(180,Number(el.duration.value)||15));
const setStatus=s=>el.status.textContent=s;
function dims(){const portrait=el.format.value==='vertical';el.canvas.width=portrait?720:1280;el.canvas.height=portrait?1280:720;render()}
function wrap(text,max){const words=String(text||'').split(/\s+/),lines=[];let line='';for(const word of words){let proposed=line?line+' '+word:word;if(ctx.measureText(proposed).width>max&&line){lines.push(line);line=word}else line=proposed}if(line)lines.push(line);return lines.slice(0,5)}
function render(){const w=el.canvas.width,h=el.canvas.height,t=Math.min(position/seconds(),1),rtl=el.lang.value==='ar';const dark=ctx.createLinearGradient(0,0,w,h);dark.addColorStop(0,'#06182b');dark.addColorStop(1,'#153d65');ctx.fillStyle=dark;ctx.fillRect(0,0,w,h);ctx.strokeStyle='rgba(255,255,255,.045)';ctx.lineWidth=1;
for(let x=40;x<w;x+=68){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}for(let y=40;y<h;y+=68){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
const pad=w*.085;ctx.fillStyle='#ee0032';ctx.fillRect(pad,h*.15,Math.min(w*.16,140),7);
ctx.textAlign=rtl?'right':'left';ctx.direction=rtl?'rtl':'ltr';const ax=rtl?w-pad:pad;ctx.font='600 '+Math.round(w*.025)+'px "Segoe UI",Tahoma,Arial,sans-serif';ctx.fillStyle='#aad8ef';ctx.fillText(rtl?'محتوى توضيحي • قيد المراجعة':'ILLUSTRATIVE • FOR REVIEW',ax,h*.12);
let scene=t<.25?0:t<.75?1:2;const content=[el.headline.value,el.detail.value,el.cta.value][scene];const size=scene===1?w*.042:w*.053;ctx.font='700 '+Math.round(size)+'px "Segoe UI",Tahoma,Arial,sans-serif';ctx.fillStyle='#fff';const lines=wrap(content,w-2*pad),step=size*1.44;let yy=h*.47-(lines.length-1)*step/2;lines.forEach((line,i)=>ctx.fillText(line,ax,yy+i*step));
ctx.fillStyle='#53bfc5';ctx.fillRect(pad,h*.83,(w-2*pad)*t,5);ctx.strokeStyle='rgba(255,255,255,.25)';ctx.strokeRect(pad,h*.83,w-2*pad,5);ctx.font='400 '+Math.round(w*.017)+'px Arial';ctx.fillStyle='#d3e5ee';ctx.fillText(scene===0?'01 / 03':scene===1?'02 / 03':'03 / 03',ax,h*.9)}
function clock(){const to=n=>{const a=Math.floor(n);return String(Math.floor(a/60)).padStart(2,'0')+':'+String(a%60).padStart(2,'0')};el.clock.textContent=to(position)+' / '+to(seconds());el.seek.max=String(seconds());el.seek.value=String(position)}
function frame(now){if(!playing)return;position=Math.min((now-start)/1000,seconds());clock();render();if(position>=seconds()){stop();return}raf=requestAnimationFrame(frame)}
function stop(){playing=false;cancelAnimationFrame(raf);el.audio.pause();if(recorder&&recorder.state==='recording'){recorder.stop()}if(!recording)setStatus('Preview stopped. Draft is not published.');}
async function play(){if(playing)return;position=Math.min(position,Math.max(0,seconds()-.01));try{if(el.audio.src){el.audio.currentTime=position;await el.audio.play()}}catch(e){setStatus('Audio playback unavailable: '+e.message);return}playing=true;start=performance.now()-position*1000;raf=requestAnimationFrame(frame)}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000)}
function json(){return {schema:'motion-studio-v1',language:el.lang.value,format:el.format.value,headline:el.headline.value,detail:el.detail.value,cta:el.cta.value,duration:Number(el.duration.value),audioAttached:!!el.audio.src,disclaimer:'illustrative-not-operational-evidence'}}
el.play.onclick=()=>void play();el.stop.onclick=stop;el.seek.oninput=()=>{position=Number(el.seek.value);if(playing){start=performance.now()-position*1000;if(el.audio.src)el.audio.currentTime=position}clock();render()};
el.narration.onchange=()=>{if(streamURL)URL.revokeObjectURL(streamURL);const f=el.narration.files?.[0];streamURL=f?URL.createObjectURL(f):null;el.audio.removeAttribute('src');el.audio.load();if(streamURL){el.audio.src=streamURL;el.audio.load()}position=0;clock();render();setStatus(f?'Local audio loaded. Video duration follows its metadata.':'Audio removed.')};
el.audio.onloadedmetadata=()=>{clock();render()};

$('evidenceFile').onchange=async()=>{
  const file=$('evidenceFile').files?.[0];if(!file)return;
  if(file.size>250000){setStatus('Evidence manifest is too large');return}
  try{openEvidence(JSON.parse(await file.text()))}
  catch(e){sourceManifest=null;setStatus('Evidence import refused: '+e.message)}
};
$('exportEvidence').onclick=()=>{
  try{download(new Blob([JSON.stringify(motionManifest(),null,2)],{type:'application/json'}),
      'motion-evidence-draft.json');setStatus('Downloaded source-linked DRAFT. Human fact-check and issuance required.')}
  catch(e){setStatus('Cannot export: '+e.message)}
};

el.save.onclick=()=>download(new Blob([JSON.stringify(json(),null,2)],{type:'application/json'}),'motion-project.json');
el.load.onclick=()=>el.project.click();el.project.onchange=async()=>{try{const f=el.project.files?.[0];if(!f)return;const p=JSON.parse(await f.text());if(p.schema!=='motion-studio-v1')throw Error('Unsupported project schema');for(const k of ['lang','format','headline','detail','cta','duration']){const field=k==='lang'?'language':k;if(p[field]!==undefined)el[k].value=String(p[field])}position=0;dims();clock();setStatus('Project loaded; reattach voice-over separately (audio bytes are never stored in JSON).')}catch(e){setStatus('Cannot open project: '+e.message)}};
async function record(){if(recording)return;const m=['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'].find(x=>MediaRecorder.isTypeSupported(x));if(!m||!el.canvas.captureStream){setStatus('This browser cannot capture WebM. Use a compatible browser or supported server renderer.');return}
recording=true;el.record.disabled=true;position=0;clock();render();const stream=el.canvas.captureStream(30);
if(el.audio.src){try{audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)();audioNode=audioNode||audioCtx.createMediaElementSource(el.audio);audioDest=audioDest||audioCtx.createMediaStreamDestination();audioNode.disconnect();audioNode.connect(audioDest);audioNode.connect(audioCtx.destination);await audioCtx.resume();for(const track of audioDest.stream.getAudioTracks())stream.addTrack(track)}catch(e){recording=false;el.record.disabled=false;setStatus('Audio capture unavailable: '+e.message);return}}
const chunks=[];recorder=new MediaRecorder(stream,{mimeType:m,videoBitsPerSecond:3500000});recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=()=>{stream.getTracks().forEach(track=>track.stop());recording=false;el.record.disabled=false;download(new Blob(chunks,{type:m}),'motion-draft.webm');setStatus('Exported actual WebM video. MP4 is not implied. Verify sound and full ending.')};recorder.onerror=e=>{setStatus('Recording failed; inspect browser support.');recording=false;el.record.disabled=false};
recorder.start(1000);setStatus('Recording real frames and optional voice-over locally.');try{await play()}catch(e){stop();setStatus('Recording could not begin: '+e.message)}}
el.record.onclick=()=>void record();for(const k of ['lang','format','headline','detail','cta','duration'])el[k].addEventListener('input',()=>{if(k==='format')dims();else{clock();render()}});
dims();clock();render();
})();
