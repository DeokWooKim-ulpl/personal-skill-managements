// 1.5.0 노트: data-doc 문서 안의 문장을 선택 → [질문하기]/[메모] → 그 문단 바로 아래에 카드가 붙고 db(BOARD.notes.collection)에 저장됨.
// 노트 문서: {doc, title, md, copy, page, quote, bnorm, qa:[{q,a,t}], memo, created, updated, synced}
//   bnorm = 붙은 문단의 정규화 글자(앞 200자). 원고가 바뀌어도 quote·bnorm으로 자리를 다시 찾음 (board.py notes_sync와 같은 규칙).
// 사본 md: Claude가 db를 읽어 board.py --notes-sync로 "원본 + 콜아웃" 사본을 만들고, 읽은 시각을 db <COL>_meta/sync {time}에 적음.
//   updated <= time 인 노트는 "md 사본에 반영됨". 페이지는 로컬 파일을 쓰지 못함.
// claude.ai 밖(db 없음)에서는 조용히 숨음. window.prompt/confirm은 아티팩트에서 막혀 있으므로 쓰지 않음.
(function(){
  var N=BOARD.notes||{},CH=BOARD.chat||{},COL=N.collection||'notes';
  var PG=(location.pathname.match(/(papers|docs)\/[^\/]+$/)||[''])[0];
  var BLOCK='p,li,tr,h1,h2,h3,h4,h5,h6,.math,pre,figure,dt,dd';
  var SKIP='.note-card,.nc-wrap,.nc-top-box,.srcbar,details.fb,.chat,.nc-tool,nav,script,style';
  var notes={},db=null,sample=null,busy=0,pending=null,tool=null,syncTime='';
  function synced(n){var u=n.updated||n.created||'';return (n.synced&&n.synced>=u)?n.synced:(syncTime&&syncTime>=u?syncTime:'');}
  function el(tag,attrs,txt){var e=document.createElement(tag);for(var k in attrs||{})e.setAttribute(k,attrs[k]);if(txt!=null)e.textContent=txt;return e;}
  function norm(s){return String(s||'').replace(/\$[^$]*\$/g,'').replace(/[^\p{L}\p{N}]+/gu,'').toLowerCase();}
  function textOf(n){if(n.nodeType===3)return n.nodeValue;if(n.nodeType!==1||n.matches('mjx-container,'+SKIP))return '';
    var s='';for(var c=n.firstChild;c;c=c.nextSibling)s+=textOf(c);return s+(/^(P|LI|TR|H\d|DIV|TD|TH|PRE)$/.test(n.tagName)?'\n':'');}
  function when(iso){if(!iso)return '';var d=new Date(iso);if(isNaN(d))return String(iso).slice(0,16);
    function z(x){return (x<10?'0':'')+x;}return (d.getMonth()+1)+'/'+d.getDate()+' '+z(d.getHours())+':'+z(d.getMinutes());}
  function typeset(n){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise([n]).catch(function(){});}
  // 답 표시용 작은 마크다운 (HTML은 모두 이스케이프, 수식은 그대로 두고 MathJax가 조판)
  function md(t){var keep=[];t=String(t||'').replace(/\$\$[\s\S]+?\$\$|\$[^$\n]+?\$/g,function(m){keep.push(m);return '\u0000'+(keep.length-1)+'\u0000';});
    function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
    function inl(s){return esc(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');}
    var out=[],list=null,para=[];
    function flush(){if(para.length){out.push('<p>'+para.map(inl).join('<br>')+'</p>');para=[];}if(list){out.push('</'+list+'>');list=null;}}
    t.split('\n').forEach(function(ln){var m;
      if(!ln.trim()){flush();return;}
      if((m=ln.match(/^\s*#{1,6}\s+(.*)/))){flush();out.push('<p class="nc-h">'+inl(m[1])+'</p>');return;}
      if((m=ln.match(/^\s*([-*•]|\d+[.)])\s+(.*)/))){var tg=/\d/.test(m[1])?'ol':'ul';if(para.length){out.push('<p>'+para.map(inl).join('<br>')+'</p>');para=[];}
        if(list!==tg){if(list)out.push('</'+list+'>');out.push('<'+tg+'>');list=tg;}out.push('<li>'+inl(m[2])+'</li>');return;}
      if(list){out.push('</'+list+'>');list=null;}para.push(ln);});
    flush();return out.join('').replace(/\u0000(\d+)\u0000/g,function(_,i){return esc(keep[+i]);});}
  function containers(root){var r=[];if(root.matches&&root.matches('[data-doc]'))r.push(root);
    [].push.apply(r,[].slice.call((root.querySelectorAll?root:document).querySelectorAll('[data-doc]')));return r;}
  function blocksOf(c){return [].slice.call(c.querySelectorAll(BLOCK)).filter(function(b){return !b.closest(SKIP)&&!b.querySelector(BLOCK.replace(/,(tr|li)\b/g,''));});}
  function blockOf(node){var e=node&&(node.nodeType===3?node.parentElement:node);if(!e||e.closest(SKIP))return null;
    var b=e.closest(BLOCK),c=e.closest('[data-doc]');return c?{c:c,b:(b&&c.contains(b))?b:e}:null;}
  function visibleDoc(){return [].slice.call(document.querySelectorAll('[data-doc]')).filter(function(s){return !s.hidden&&s.offsetParent!==null;})[0]||null;}
  function info(c){return {doc:c.dataset.doc,title:c.dataset.title||'',md:c.dataset.md||'',copy:c.dataset.copy||'',page:PG};}
  function where(n){var b=document.querySelector('nav.top button[data-t="'+String(n.doc).split('-')[0]+'"]');return (n.page?'':(b?b.textContent+' > ':''))+(n.title||n.doc);}
  function copyText(s,btn){function ok(){var o=btn.textContent;btn.textContent='복사됨';setTimeout(function(){btn.textContent=o;},1400);}
    function fallback(){var ta=el('textarea');ta.value=s;ta.style.cssText='position:fixed;opacity:0';document.body.appendChild(ta);ta.select();
      var done=false;try{done=document.execCommand('copy');}catch(e){}ta.remove();
      if(done)ok();else{var sp=btn.parentNode.querySelector('code');if(sp){var r=document.createRange();r.selectNodeContents(sp);var g=getSelection();g.removeAllRanges();g.addRange(r);}btn.textContent='Ctrl+C로 복사';}}
    try{navigator.clipboard.writeText(s).then(ok,fallback);}catch(e){fallback();}}
  document.addEventListener('click',function(e){var b=e.target.closest('[data-copy]');if(b&&b.tagName==='BUTTON'){e.preventDefault();copyText(b.dataset.copy,b);}});

  // ---------------------------------------------------------------- 카드
  function card(id,n,draft){
    var cd=el('div',{class:'note-card'+(draft?' draft':''),'data-id':id||''});
    var top=el('div',{class:'nc-head'});var qa=n.qa||[];
    top.appendChild(el('span',{class:'nc-kind'},qa.length?'❓ 질문 '+qa.length+'개':'📝 메모'));
    top.appendChild(el('span',{class:'nc-when'},draft?'새 노트':when(n.updated||n.created)));
    var sp=el('span',{class:'nc-sp'});top.appendChild(sp);
    if(!draft){var fold=el('button',{type:'button','data-a':'fold'},'접기');top.appendChild(fold);
      top.appendChild(el('button',{type:'button','data-a':'del'},'삭제'));}
    else top.appendChild(el('button',{type:'button','data-a':'cancel'},'취소'));
    cd.appendChild(top);
    if(n.quote)cd.appendChild(el('div',{class:'nc-quote'},'“'+n.quote+'”'));
    var list=el('div',{class:'nc-qa'});
    qa.forEach(function(x,k){list.appendChild(qaItem(x,k));});cd.appendChild(list);
    var memo=el('div',{class:'nc-memo'});memo.appendChild(el('span',{class:'nc-label'},'📝 내 정리'));
    var mv=el('div',{class:'nc-memo-view'});if(n.memo){mv.innerHTML=md(n.memo);}else{mv.appendChild(el('span',{class:'meta'},draft&&!n.ask?'':'아직 없음 — 답을 읽고 내 말로 정리해 두세요.'));}
    var mt=el('textarea',{class:'nc-memo-edit',placeholder:'내 말로 정리 (수식은 $...$)',hidden:''});mt.value=n.memo||'';
    var mrow=el('div',{class:'nc-row'});
    var mbtn=el('button',{type:'button','data-a':'memo'},n.memo?'정리 고치기':'정리 쓰기');var msave=el('button',{type:'button','data-a':'msave',hidden:''},'저장');
    mrow.appendChild(mbtn);mrow.appendChild(msave);memo.appendChild(mv);memo.appendChild(mt);memo.appendChild(mrow);
    var ask=el('form',{class:'nc-ask'});var at=el('textarea',{placeholder:qa.length?'이 부분에 대해 이어서 묻기…':'이 부분에 대해 묻기 (예: 이 식이 왜 이렇게 되나요?)'});
    var arow=el('div',{class:'nc-row'});var tier=el('select',{'aria-label':'답의 깊이'});
    [['quick','빠름'],['default','보통'],['complex','깊게']].forEach(function(o){var op=el('option',{value:o[0]},o[1]);if(o[0]===(N.ask_tier||'default'))op.selected=true;tier.appendChild(op);});
    var go=el('button',{type:'submit'},'묻기'),stop=el('button',{type:'button','data-a':'stop',hidden:''},'멈춤'),msg=el('span',{class:'nc-msg'});
    arow.appendChild(go);arow.appendChild(tier);arow.appendChild(stop);arow.appendChild(msg);ask.appendChild(at);ask.appendChild(arow);
    if(draft&&n.memoOnly){cd.appendChild(memo);mv.hidden=true;mt.hidden=false;mbtn.hidden=true;msave.hidden=false;}
    else{cd.appendChild(ask);if(sample===null){ask.hidden=true;}cd.appendChild(memo);if(draft)memo.hidden=true;}
    if(!draft){var sy=el('div',{class:'nc-sync'});
      var st=synced(n);sy.textContent=st?'md 사본에 반영됨 · '+when(st):'md 사본 반영 대기 (다음 동기화 때)';
      sy.className='nc-sync '+(st?'ok':'wait');cd.appendChild(sy);}
    cd._n=n;cd._ctl=null;
    // 동작
    cd.addEventListener('click',function(e){var a=e.target.dataset&&e.target.dataset.a;if(!a)return;
      if(a==='fold'){cd.classList.toggle('folded');e.target.textContent=cd.classList.contains('folded')?'펼치기':'접기';}
      if(a==='cancel'){cd.remove();pending=null;}
      if(a==='del'){if(e.target.dataset.sure){e.target.disabled=true;db.collection(COL).doc(id).delete().catch(function(err){msg.textContent='지우지 못함 ('+err.code+')';});}
        else{e.target.dataset.sure='1';e.target.textContent='정말 삭제?';setTimeout(function(){if(e.target.isConnected){delete e.target.dataset.sure;e.target.textContent='삭제';}},3500);}}
      if(a==='memo'){mv.hidden=true;mt.hidden=false;mbtn.hidden=true;msave.hidden=false;mt.focus();}
      if(a==='msave'){var v=mt.value.trim();msave.disabled=true;
        var p=draft?create(Object.assign({},n,{memo:v,qa:n.qa||[]})):db.collection(COL).doc(id).update({memo:v,updated:new Date().toISOString()});
        p.then(function(){if(draft)cd.remove();else{mv.innerHTML=v?md(v):'';mv.hidden=false;mt.hidden=true;mbtn.hidden=false;msave.hidden=true;msave.disabled=false;typeset(mv);}},
          function(err){msave.disabled=false;msave.textContent='다시 저장 ('+(err.code||'오류')+')';});}
      if(a==='stop'&&cd._ctl)cd._ctl.abort();});
    ask.addEventListener('submit',function(e){e.preventDefault();var q=at.value.trim();if(!q||cd._ctl)return;
      var item=qaItem({q:q,a:''},qa.length,true);list.appendChild(item);at.value='';msg.textContent='';
      var aEl=item.querySelector('.nc-a');aEl.textContent='생각하는 중…';
      var c=cd.closest('[data-doc]')||visibleDoc();
      var msgs=[];var ctx=(CH.rules||'')+'\n\n[문서] '+(n.title||'')+'\n'+(c?textOf(c).replace(/\n{3,}/g,'\n\n').slice(0,N.max_context||30000):'')+
        (n.quote?'\n\n[선택한 부분 — 이 부분을 중심으로 설명]\n'+n.quote:'');
      (n.qa||[]).forEach(function(x,k){msgs.push({role:'user',content:(k?'':ctx+'\n\n[질문]\n')+x.q});msgs.push({role:'assistant',content:x.a});});
      msgs.push({role:'user',content:(msgs.length?'':ctx+'\n\n[질문]\n')+q});
      cd._ctl=new AbortController();stop.hidden=false;go.disabled=true;busy++;
      sample(msgs,{modelTier:tier.value,cache:false,signal:cd._ctl.signal,onText:function(u){aEl.textContent=u.text;}}).then(function(r){
        aEl.innerHTML=md(r.text);typeset(aEl);var nq=(n.qa||[]).concat([{q:q,a:r.text.slice(0,60000),t:new Date().toISOString()}]);
        var p=draft?create(Object.assign({},n,{qa:nq})):db.collection(COL).doc(id).update({qa:nq,updated:new Date().toISOString()});
        return p.then(function(){n.qa=nq;if(draft){cd.remove();}else{memo.hidden=false;}msg.textContent='저장됨';},function(err){msg.textContent='답을 저장하지 못함 ('+(err.code||'오류')+')';});
      },function(err){aEl.textContent=(err.text||'')+(err.code==='cancelled'?'\n(멈춤)':'\n(답을 받지 못했습니다: '+err.code+')');if(err.code==='not_granted')ask.hidden=true;})
      .then(function(){cd._ctl=null;stop.hidden=true;go.disabled=false;busy=Math.max(0,busy-1);if(!busy)renderAll();});});
    at.addEventListener('keydown',function(k){if(k.key==='Enter'&&(k.ctrlKey||k.metaKey)){k.preventDefault();ask.requestSubmit();}});
    if(draft)setTimeout(function(){(n.memoOnly?mt:at).focus();},30);
    return cd;}
  function qaItem(x,k,live){var it=el('div',{class:'nc-item'});it.appendChild(el('div',{class:'nc-q'},'Q'+(k+1)+'. '+x.q));
    var a=el('div',{class:'nc-a'});if(!live){a.innerHTML=md(x.a);}it.appendChild(a);
    if(!live&&String(x.a||'').length>700){a.classList.add('clamp');var more=el('button',{type:'button',class:'nc-more'},'답 전체 보기');
      more.onclick=function(){a.classList.toggle('clamp');more.textContent=a.classList.contains('clamp')?'답 전체 보기':'답 줄이기';};it.appendChild(more);}
    return it;}
  function create(n){var now=new Date().toISOString();
    var d={doc:n.doc,title:n.title||'',md:n.md||'',copy:n.copy||'',page:n.page||'',quote:(n.quote||'').slice(0,1200),bnorm:(n.bnorm||'').slice(0,200),
      qa:n.qa||[],memo:n.memo||'',created:now,updated:now};
    return db.collection(COL).add(d);}

  // ---------------------------------------------------------------- 문서에 붙이기
  function locate(c,n,bl){var q=norm(n.quote),bn=n.bnorm||'',k,t;
    var ns=bl.map(function(b){return norm(textOf(b));});
    if(q.length>=4){for(k=0;k<ns.length;k++)if(ns[k].indexOf(q)>=0&&(!bn||ns[k].indexOf(bn.slice(0,20))>=0||bn.indexOf(ns[k].slice(0,20))>=0))return bl[k];
      for(k=0;k<ns.length;k++)if(ns[k].indexOf(q)>=0)return bl[k];}
    if(bn.length>=8)for(k=0;k<ns.length;k++){t=ns[k];if(t.indexOf(bn.slice(0,40))>=0||(t.length>=8&&bn.indexOf(t)===0))return bl[k];}
    return null;}
  function holder(b){var at=b.tagName==='TR'?(b.closest('.tbl')||b.closest('table')):b;
    if(b.tagName==='LI'){var h=b.querySelector(':scope > .nc-wrap');if(!h){h=el('div',{class:'nc-wrap'});b.appendChild(h);}return h;}
    var nx=at.nextElementSibling;if(nx&&nx.classList.contains('nc-wrap'))return nx;var w=el('div',{class:'nc-wrap'});at.after(w);return w;}
  function render(c){if(c.querySelector('.note-card.draft')||(busy&&c.querySelector('.note-card')))return;
    var act=document.activeElement;if(act&&c.contains(act)&&act.closest('.note-card'))return;
    var fold={};c.querySelectorAll('.note-card.folded').forEach(function(x){fold[x.dataset.id]=1;});
    c.querySelectorAll('.nc-wrap,.nc-top-box').forEach(function(x){x.remove();});c.querySelectorAll('.has-note').forEach(function(x){x.classList.remove('has-note');});
    var mine=Object.keys(notes).filter(function(id){return notes[id].doc===c.dataset.doc;}).sort(function(a,b){return String(notes[a].created).localeCompare(String(notes[b].created));});
    if(!mine.length)return;var bl=blocksOf(c),loose=[];
    mine.forEach(function(id){var n=notes[id],b=(n.quote||n.bnorm)?locate(c,n,bl):null;var cd=card(id,n);if(fold[id])cd.classList.add('folded');
      if(b){b.classList.add('has-note');holder(b).appendChild(cd);}else loose.push(cd);});
    if(loose.length){var box=el('div',{class:'nc-top-box'});box.appendChild(el('div',{class:'nc-label'},'이 문서 전체에 단 노트 · 원문이 바뀌어 자리를 못 찾은 노트'));
      loose.forEach(function(x){box.appendChild(x);});var sb=c.querySelector(':scope > .srcbar');if(sb)sb.after(box);else c.prepend(box);}
    typeset(c);}
  function renderAll(root){containers(root||document).forEach(render);overview();}

  // ---------------------------------------------------------------- 선택 도구 (질문하기 / 메모)
  function hideTool(){if(tool)tool.hidden=true;}
  function showTool(){var s=getSelection();if(!s||s.isCollapsed||!s.rangeCount){hideTool();return;}
    var txt=String(s).trim();if(txt.length<2){hideTool();return;}
    var hit=blockOf(s.anchorNode);if(!hit||!hit.c.contains(s.focusNode)){hideTool();return;}
    pending={c:hit.c,b:hit.b,quote:txt.slice(0,1200)};
    if(!tool){tool=el('div',{class:'nc-tool',hidden:''});
      var qb=el('button',{type:'button','data-t':'ask'},'❓ 질문하기'),mb=el('button',{type:'button','data-t':'memo'},'📝 메모');
      if(sample===null)qb.hidden=true;tool.appendChild(qb);tool.appendChild(mb);document.body.appendChild(tool);
      tool.addEventListener('mousedown',function(e){e.preventDefault();});
      tool.addEventListener('click',function(e){var t=e.target.dataset&&e.target.dataset.t;if(!t||!pending)return;startDraft(pending,t==='memo');hideTool();});}
    var r=s.getRangeAt(0).getBoundingClientRect();tool.hidden=false;
    var x=Math.min(Math.max(8,r.left+window.scrollX),window.scrollX+document.documentElement.clientWidth-tool.offsetWidth-8);
    var y=r.top+window.scrollY-tool.offsetHeight-8;if(y<window.scrollY+4)y=r.bottom+window.scrollY+8;
    tool.style.left=x+'px';tool.style.top=y+'px';}
  function startDraft(p,memoOnly){var c=p.c;c.querySelectorAll('.note-card.draft').forEach(function(x){x.remove();});
    var n=Object.assign(info(c),{quote:p.quote,bnorm:norm(textOf(p.b)).slice(0,200),qa:[],memo:'',memoOnly:memoOnly});
    var cd=card('',n,true);p.b.classList.add('has-note');holder(p.b).appendChild(cd);try{getSelection().removeAllRanges();}catch(e){}
    cd.scrollIntoView({block:'nearest',behavior:'smooth'});}
  var tmr=null;document.addEventListener('selectionchange',function(){clearTimeout(tmr);tmr=setTimeout(showTool,220);});
  document.addEventListener('scroll',function(){if(tool&&!tool.hidden)showTool();},{passive:true});

  // ---------------------------------------------------------------- 질문 창 답 → 노트로 붙이기
  document.addEventListener('board:qa',function(e){var d=e.detail||{};if(!db||!d.el)return;
    var b=el('button',{type:'button',class:'nc-pin'},'📌 이 답을 노트로 붙이기');d.el.after(b);
    b.onclick=function(){var c=visibleDoc();if(!c){b.textContent='붙일 문서가 없음';return;}b.disabled=true;
      var bl=blocksOf(c),q=norm(d.sel),blk=null;if(q.length>=4)blk=bl.filter(function(x){return norm(textOf(x)).indexOf(q)>=0;})[0]||null;
      create(Object.assign(info(c),{quote:d.sel||'',bnorm:blk?norm(textOf(blk)).slice(0,200):'',qa:[{q:d.q,a:d.a,t:new Date().toISOString()}]}))
        .then(function(){b.textContent='노트에 붙였습니다 ('+(c.dataset.title||'')+')';},function(err){b.disabled=false;b.textContent='붙이지 못함 ('+(err.code||'오류')+')';});};});

  // ---------------------------------------------------------------- 내 노트 모음 · 최근 노트
  function goTo(id){var n=notes[id];if(!n)return;
    if(n.page&&n.page!==PG){location.href=(PG?'../':'')+n.page+'#note-'+id;return;}
    var parts=String(n.doc).split('-'),t=parts[0],s=parts.slice(1).join('-');
    var tb=document.querySelector('nav.top button[data-t="'+t+'"]');if(tb)tb.click();
    var tries=0;(function wait(){var sb=document.querySelector('#top-'+t+' nav.sub button[data-s="'+s+'"]'),sec=document.getElementById('sub-'+t+'-'+s);
      if(sb&&sb.getAttribute('aria-selected')!=='true')sb.click();
      var cd=sec&&sec.querySelector('.note-card[data-id="'+id+'"]');
      if(!cd&&sec&&sec.dataset.doc&&tries===3)render(sec);
      if(cd){cd.scrollIntoView({block:'center',behavior:'smooth'});cd.classList.add('flash');setTimeout(function(){cd.classList.remove('flash');},1800);}
      else if(tries++<40)setTimeout(wait,150);})();}
  function mini(id,n){var it=el('div',{class:'nc-mini'});var h=el('div',{class:'nc-mini-h'});
    h.appendChild(el('span',{class:'chip '+((n.qa||[]).length?'ac':'mute')},(n.qa||[]).length?'질문 '+n.qa.length:'메모'));
    h.appendChild(el('span',{class:'nc-mini-w'},' '+when(n.updated||n.created)+' · '+where(n)));
    var g=el('button',{type:'button'},'그 자리로 가기 →');g.onclick=function(){goTo(id);};h.appendChild(g);it.appendChild(h);
    if(n.quote)it.appendChild(el('div',{class:'nc-quote'},'“'+n.quote.slice(0,220)+(n.quote.length>220?'…':'')+'”'));
    (n.qa||[]).forEach(function(x,k){var q=el('details',{class:'nc-mini-q'});q.appendChild(el('summary',null,'Q'+(k+1)+'. '+x.q));
      var a=el('div',{class:'nc-a'});a.innerHTML=md(x.a);q.appendChild(a);q.addEventListener('toggle',function(){if(q.open)typeset(a);},{once:true});it.appendChild(q);});
    if(n.memo){var m=el('div',{class:'nc-memo-view'});m.innerHTML='<span class="nc-label">📝 내 정리</span>'+md(n.memo);it.appendChild(m);}
    return it;}
  function overview(){var all=document.getElementById('notes-all'),rec=document.getElementById('notes-recent');
    var ids=Object.keys(notes).sort(function(a,b){return String(notes[b].updated||notes[b].created).localeCompare(String(notes[a].updated||notes[a].created));});
    if(rec){rec.innerHTML='';var k=+rec.dataset.n||5;
      if(!ids.length)rec.appendChild(el('p',{class:'meta'},'아직 노트가 없습니다. 논문화 탭에서 문장을 선택해 질문해 보세요.'));
      ids.slice(0,k).forEach(function(id){rec.appendChild(mini(id,notes[id]));});typeset(rec);}
    if(!all)return;var f=all.querySelector('.nc-filter');var qv=f?f.value:'';all.innerHTML='';
    var wait=ids.filter(function(id){return !synced(notes[id]);}).length;
    var head=el('div',{class:'nc-sum'});
    head.appendChild(el('span',null,'노트 '+ids.length+'개 · 질문 '+ids.reduce(function(s,id){return s+(notes[id].qa||[]).length;},0)+'개 · md 사본 반영 대기 '+wait+'개'));
    all.appendChild(head);
    var inp=el('input',{type:'search',class:'nc-filter',placeholder:'노트 찾기 (질문·답·메모·선택 문장)'});inp.value=qv;all.appendChild(inp);
    inp.addEventListener('input',function(){clearTimeout(inp._t);inp._t=setTimeout(function(){overview();var x=document.querySelector('#notes-all .nc-filter');if(x){x.focus();x.setSelectionRange(x.value.length,x.value.length);}},250);});
    if(!ids.length){all.appendChild(el('p',{class:'meta'},'아직 노트가 없습니다.'));return;}
    var nq=norm(qv),groups={},order=[];
    ids.forEach(function(id){var n=notes[id];if(nq&&norm([n.quote,n.memo,n.title].concat((n.qa||[]).map(function(x){return x.q+' '+x.a;})).join(' ')).indexOf(nq)<0)return;
      if(!groups[n.doc]){groups[n.doc]=[];order.push(n.doc);}groups[n.doc].push(id);});
    order.forEach(function(doc){var g=el('section',{class:'nc-group'}),n0=notes[groups[doc][0]];
      g.appendChild(el('h3',null,where(n0)+' ('+groups[doc].length+')'));
      if(n0.copy){var sb=el('div',{class:'srcbar'});var it=el('span',{class:'sb-item'});it.appendChild(el('span',{class:'sb-k'},'노트 사본'));
        var p=(N.root_abs||'')+'\\'+n0.copy.replace(/\//g,'\\');it.appendChild(el('code',{class:'sb-path',title:p},n0.copy.split('/').pop()));
        it.appendChild(el('button',{type:'button',class:'sb-copy','data-copy':p,title:'전체 경로 복사'},'경로 복사'));sb.appendChild(it);g.appendChild(sb);}
      groups[doc].forEach(function(id){g.appendChild(mini(id,notes[id]));});all.appendChild(g);});
    if(!order.length)all.appendChild(el('p',{class:'meta'},'찾는 말이 들어간 노트가 없습니다.'));
    typeset(all);}

  // ---------------------------------------------------------------- 시작
  var hint=null;
  function setHint(t){document.querySelectorAll('.nc-hint').forEach(function(x){x.textContent=t;});}
  Promise.all([window.claude?claude.use('db'):null,window.claude&&CH.enabled!==false?claude.use('sample'):null]).then(function(r){
    db=r[0];sample=r[1]||null;
    if(!db){setHint('노트는 claude.ai에서 열었을 때만 동작합니다.');var a=document.getElementById('notes-all');if(a)a.innerHTML='<p class="meta">노트는 claude.ai에서 열었을 때만 보입니다.</p>';return;}
    setHint(N.hint||'');
    var timer=setTimeout(function(){var a=document.getElementById('notes-all');if(a&&!Object.keys(notes).length)a.innerHTML='<p class="meta">노트를 불러오지 못했습니다.</p>';},10000);
    db.collection(COL).onSnapshot(function(snap){clearTimeout(timer);var nx={};snap.docs.forEach(function(d){nx[d.id]=d.data()||{};});notes=nx;
      if(!busy)renderAll();
      var m=location.hash.match(/^#note-(.+)$/);if(m&&notes[m[1]]&&!hint){hint=1;setTimeout(function(){goTo(m[1]);},300);}},
      function(err){clearTimeout(timer);var a=document.getElementById('notes-all');if(a)a.innerHTML='<p class="meta">노트를 불러오지 못했습니다 ('+err.code+').</p>';});
    try{db.doc(COL+'_meta/sync').onSnapshot(function(s){var t=(s&&s.exists&&(s.data()||{}).time)||'';if(t!==syncTime){syncTime=t;if(!busy)renderAll();}},function(){});}catch(e){}
    document.addEventListener('board:pane',function(e){renderAll(e.detail);});
  });
})();
