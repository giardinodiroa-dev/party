// Every scene: window.scene = (tl) => build its GSAP timeline; the stage plays only on click.
(function(){
  const root = document.querySelector('.stage'); const btn = document.createElement('button');
  btn.className='play'; btn.innerHTML='<span>▶ PLAY</span>'; root.appendChild(btn);
  let tl=null;
  btn.addEventListener('click', ()=>{
    if (tl) tl.kill();
    tl = gsap.timeline({onComplete: ()=>{ btn.innerHTML='<span>↻ REPLAY</span>'; btn.classList.remove('hidden'); }});
    btn.classList.add('hidden');
    window.scene(tl);
  });
  // captions helper
  window.say = (tl, sel, text, at, dur) => { const el = document.querySelector(sel); tl.call(()=>{el.textContent=text}, null, at); tl.to(el,{opacity:.85,duration:.6},at); tl.to(el,{opacity:0,duration:.6},at+dur); };
})();
