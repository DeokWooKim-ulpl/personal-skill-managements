// 입력함(db "inbox")과 질문 창(sample). BOARD 설정은 board.py가 앞에 넣는다. claude.ai 밖에서 열면 둘 다 조용히 숨는다.
// inbox 문서: {kind, target, text, ctx, created, status: "new"|"done", reply}
// chatlog 문서 (1.3.0): {where, sel, q, a, tier, page, created, status: "new"|"done"} — 질문 창의 질문·답 한 쌍마다 하나. 처리하는 쪽이 정돈해 질문 기록 원고로 옮김.
// 아티팩트 안에서는 window.prompt/alert가 막혀 있으므로 쓰지 않는다 (1.3.0: 스킵·수정 요청 버튼이 동작하지 않던 원인).
(function(){
  var IB=BOARD.inbox,CH=BOARD.chat;
  var isPaper=/\/(papers|docs)\//.test(location.pathname);
  function where(el){
    if(isPaper)return 'page: '+(document.querySelector('h1')||{}).textContent;
    var sec=el&&el.closest('section.panel');if(!sec)return BOARD.name;
    var p=sec.id.split('-'),t=document.querySelector('nav.top button[data-t="'+p[1]+'"]'),
        s=document.querySelector('#top-'+p[1]+' nav.sub button[data-s="'+p.slice(2).join('-')+'"]');
    return (t?t.textContent:'')+' > '+(s?s.textContent:'');}
  function visiblePanel(){return isPaper?document.querySelector('.wrap'):[].slice.call(document.querySelectorAll('section.panel')).filter(function(s){return !s.hidden&&s.offsetParent;})[0];}
  function visibleText(){var e=visiblePanel();return e?e.innerText.slice(0,CH.page_chars||24000):'';}
  function el(tag,attrs,txt){var e=document.createElement(tag);for(var k in attrs||{})e.setAttribute(k,attrs[k]);if(txt!=null)e.textContent=txt;return e;}
  function store(k,v){try{if(v===undefined)return JSON.parse(localStorage.getItem(k)||'null');localStorage.setItem(k,JSON.stringify(v));}catch(e){return null;}}
  var dbP=(window.claude&&(IB.enabled||CH.log))?claude.use('db'):Promise.resolve(null);
  var smP=(window.claude&&CH.enabled)?claude.use('sample'):Promise.resolve(null);

  async function send(doc){var db=await dbP;if(!db||!IB.enabled)throw {code:'no_db'};
    doc.created=new Date().toISOString();doc.status='new';doc.reply='';return db.collection('inbox').add(doc);}
  async function logChat(doc){var db=await dbP;if(!db||!CH.log)return;
    doc.created=new Date().toISOString();doc.status='new';
    try{await db.collection(CH.log_collection||'chatlog').add(doc);}catch(e){}}

  dbP.then(function(db){
    if(!db||!IB.enabled){var l=document.getElementById('inbox-list');if(l)l.innerHTML='<p class="meta">입력 기능은 claude.ai에서 열었을 때만 동작합니다.</p>';
      document.querySelectorAll('button.act').forEach(function(b){b.hidden=true;});return;}
    // 탭 내용을 따로 불러오는 보고판(lazy_tabs)은 탭이 열릴 때마다 board:pane 이벤트로 새 패널이 들어옴 (1.3.0)
    function attach(root){
    var panels=isPaper?[document.querySelector('.wrap')]:[].slice.call(root.querySelectorAll('section.panel')).filter(function(s){return !s.querySelector('#inbox-list')&&!s.querySelector(':scope > details.fb');});
    panels.forEach(function(sec){
      var d=el('details',{class:'fb'});d.appendChild(el('summary',null,IB.summary));
      var f=el('form');var sel=el('select');IB.kinds.forEach(function(k){sel.appendChild(el('option',{value:k},k));});
      var ta=el('textarea',{placeholder:IB.placeholder});
      var row=el('div',{class:'row'});var b=el('button',{type:'submit'},IB.send);var msg=el('span',{class:'fbmsg'});
      row.appendChild(b);row.appendChild(msg);f.appendChild(sel);f.appendChild(ta);f.appendChild(row);d.appendChild(f);sec.appendChild(d);
      f.addEventListener('submit',async function(e){e.preventDefault();if(!ta.value.trim())return;b.disabled=true;msg.textContent='보내는 중…';
        try{await send({kind:sel.value,target:where(sec),text:ta.value.trim(),ctx:String(getSelection()||'').slice(0,1500)});
          ta.value='';msg.textContent='보냈습니다. '+IB.processed_by;}
        catch(err){msg.textContent='보내지 못했습니다 ('+(err.code||'오류')+').';}b.disabled=false;});
    });
    var lst=root.querySelector&&root.querySelector('#inbox-list');if(lst&&!lst.dataset.on){lst.dataset.on='1';showList(lst);}
    }
    // 한 번 누르는 버튼(스킵 등): 버튼 옆에 메모 칸과 [보내기][취소]를 펼침 (prompt 대신)
    document.addEventListener('click',async function(e){
      var b=e.target.closest('button.act');
      if(b&&!b.dataset.open&&!b.disabled){b.dataset.open='1';
        var box=el('span',{class:'act-note'});var inp=el('input',{type:'text',placeholder:'남길 말 (없으면 비워 두고 보내기)'});
        var ok=el('button',{type:'button'},'보내기'),no=el('button',{type:'button'},'취소');
        box.appendChild(inp);box.appendChild(ok);box.appendChild(no);b.after(box);inp.focus();
        no.onclick=function(){box.remove();delete b.dataset.open;};
        ok.onclick=async function(){ok.disabled=true;
          try{await send({kind:b.dataset.kind,target:b.dataset.target,text:inp.value.trim()||b.dataset.kind,ctx:''});
            box.remove();b.textContent='보냄';b.disabled=true;}
          catch(err){ok.disabled=false;ok.textContent='다시 보내기 ('+(err.code||'오류')+')';}};
        inp.addEventListener('keydown',function(k){if(k.key==='Enter'){k.preventDefault();ok.click();}});}});
    function showList(list){
    var timer=setTimeout(function(){list.innerHTML='<p class="meta">목록을 불러오지 못했습니다.</p>';},10000);
    db.collection('inbox').orderBy('created','desc').limit(60).onSnapshot(function(snap){clearTimeout(timer);list.innerHTML='';
      if(snap.empty){list.appendChild(el('p',{class:'meta'},'아직 보낸 의견이 없습니다.'));return;}
      snap.docs.forEach(function(d){var x=d.data()||{};var box=el('div',{class:'inbox-item'});
        var h=el('div');h.appendChild(el('span',{class:'chip '+(x.status==='done'?'ok':'mid')},x.status==='done'?'처리됨':'대기'));
        h.appendChild(document.createTextNode(' '+(x.kind||'')+' · '+(x.target||'')+' · '+String(x.created||'').slice(0,16).replace('T',' ')));
        box.appendChild(h);box.appendChild(el('div',null,x.text||''));
        if(x.reply)box.appendChild(el('div',{class:'reply'},IB.reply_prefix+x.reply));list.appendChild(box);});
    },function(){clearTimeout(timer);list.innerHTML='<p class="meta">목록을 불러오지 못했습니다.</p>';});
    }
    attach(document);
    document.addEventListener('board:pane',function(e){attach(e.detail);});
  });

  smP.then(function(sample){if(!sample)return;
    var fab=el('button',{type:'button',class:'chat-fab'},CH.fab);var box=el('div',{class:'chat',hidden:''});
    var grip=el('div',{class:'grip',title:'끌어서 크기 조절 (두 번 누르면 원래 크기)'});box.appendChild(grip);
    var hd=el('div',{class:'row'});var ttl=el('strong',{style:'flex:1'},CH.title);var tier=el('select',{'aria-label':'모델'});
    [['quick','빠름'],['default','보통'],['complex','깊게']].forEach(function(o){var op=el('option',{value:o[0]},o[1]);if(o[0]===CH.default_tier)op.selected=true;tier.appendChild(op);});
    hd.appendChild(ttl);hd.appendChild(tier);hd.appendChild(el('button',{type:'button','data-x':'new'},'새 대화'));hd.appendChild(el('button',{type:'button','data-x':'close'},'닫기'));
    box.appendChild(hd);box.appendChild(el('p',{class:'meta',style:'margin:0'},CH.note+(CH.log?' 질문과 답은 질문 기록으로 저장되어 정리됩니다.':'')));
    var log=el('div',{class:'log'}),selBox=el('div',{class:'sel',hidden:''}),form=el('form'),ta=el('textarea',{placeholder:CH.placeholder});
    // 선택한 부분: 글자와 [선택 해제] 버튼 (1.4.0 — 원하지 않는 선택을 질문에서 뺄 수 있게)
    var selText=el('span',{class:'sel-t'}),selClear=el('button',{type:'button','data-x':'unsel',title:'선택한 부분을 질문에 넣지 않음'},'선택 해제');
    selBox.appendChild(selText);selBox.appendChild(selClear);
    var row=el('div',{class:'row'}),stop=el('button',{type:'button','data-x':'stop',hidden:''},'멈춤'),msg=el('span',{class:'fbmsg'});
    row.appendChild(el('button',{type:'submit'},'묻기'));row.appendChild(stop);
    if(IB.enabled)row.appendChild(el('button',{type:'button','data-x':'send',title:'입력 칸에 적은 말을 고쳐 달라는 요청으로, 위 대화와 함께 보냅니다'},'이 대화를 수정 요청으로 보내기'));
    row.appendChild(msg);form.appendChild(ta);form.appendChild(row);box.appendChild(log);box.appendChild(selBox);box.appendChild(form);
    document.body.appendChild(fab);document.body.appendChild(box);
    // 크기 조절: 창이 오른쪽 아래에 붙어 있으므로 왼쪽 위 손잡이로 끌어 넓히고 높임. 크기는 이 브라우저에 기억함.
    var SK='board-chat-size:'+(BOARD.name||'');
    function applySize(s){if(!s){box.style.width='';box.style.height='';box.style.maxHeight='';return;}
      var w=Math.max(300,Math.min(s.w,innerWidth-24)),h=Math.max(260,Math.min(s.h,innerHeight-90));
      box.style.width=w+'px';box.style.height=h+'px';box.style.maxHeight='none';}
    applySize(store(SK));
    grip.addEventListener('pointerdown',function(e){e.preventDefault();grip.setPointerCapture(e.pointerId);
      var r=box.getBoundingClientRect(),x0=e.clientX,y0=e.clientY,w0=r.width,h0=r.height;
      function mv(ev){applySize({w:w0+(x0-ev.clientX),h:h0+(y0-ev.clientY)});}
      function up(){grip.removeEventListener('pointermove',mv);grip.removeEventListener('pointerup',up);
        var rr=box.getBoundingClientRect();store(SK,{w:rr.width,h:rr.height});}
      grip.addEventListener('pointermove',mv);grip.addEventListener('pointerup',up);});
    grip.addEventListener('dblclick',function(){applySize(null);store(SK,null);});
    var turns=[],picked='',ctl=null,ctxWhere='',MAX=CH.max_turns||12;
    function add(cls,t){var m=el('div',{class:'m '+cls},t);log.appendChild(m);log.scrollTop=log.scrollHeight;return m;}
    function typeset(n){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise([n]).catch(function(){});}
    document.addEventListener('selectionchange',function(){var s=String(getSelection()||'').trim();
      if(s&&!box.contains(getSelection().anchorNode)){picked=s.slice(0,2000);selBox.hidden=false;selText.textContent='선택한 부분: '+picked;}});
    function unselect(){picked='';selBox.hidden=true;selText.textContent='';try{getSelection().removeAllRanges();}catch(e){}}
    fab.onclick=function(){box.hidden=!box.hidden;if(!box.hidden)ta.focus();};
    box.addEventListener('click',function(e){var x=e.target.dataset&&e.target.dataset.x;
      if(x==='close')box.hidden=true;
      if(x==='unsel'){unselect();ta.focus();}
      if(x==='new'){turns=[];log.innerHTML='';unselect();msg.textContent='';}
      if(x==='stop'&&ctl)ctl.abort();
      if(x==='send'){var note=ta.value.trim();
        if(!turns.length&&!note){msg.textContent='고쳐 달라는 내용을 입력 칸에 적은 뒤 누르세요.';return;}
        var conv=turns.map(function(t){return (t.role==='user'?'Q: ':'A: ')+t.content.replace(/^\[페이지 내용\][\s\S]*?(?=\[선택한 부분\]|\[질문\])/,'').replace(/^\[질문\]\n/,'');}).join('\n\n').slice(0,6000);
        var sb=e.target;sb.disabled=true;msg.textContent='보내는 중…';
        send({kind:'수정 요청',target:ctxWhere||where(isPaper?null:visiblePanel()),text:note||'질문 창 대화 내용을 반영해 주세요',ctx:conv}).then(function(){
            msg.textContent='수정 요청을 보냈습니다. '+IB.processed_by;ta.value='';sb.disabled=false;},
          function(err){msg.textContent='보내지 못했습니다 ('+(err.code||'오류')+').';sb.disabled=false;});}});
    form.addEventListener('submit',async function(e){e.preventDefault();var q=ta.value.trim();if(!q||ctl)return;
      ctxWhere=where(isPaper?null:visiblePanel());var qPicked=picked;
      var content=(turns.length?'':'[페이지 내용] ('+ctxWhere+')\n'+visibleText()+'\n\n')+(picked?'[선택한 부분]\n'+picked+'\n\n':'')+'[질문]\n'+q;
      add('u',q+(picked?'\n(선택한 부분 포함)':''));turns.push({role:'user',content:content});ta.value='';picked='';selBox.hidden=true;msg.textContent='';
      var m=add('a','생각하는 중…');ctl=new AbortController();stop.hidden=false;
      try{var r=await sample([{role:'user',content:CH.rules}].concat(turns.length>MAX?[turns[0]].concat(turns.slice(-(MAX-1))):turns),{modelTier:tier.value,cache:false,signal:ctl.signal,
          onText:function(u){m.textContent=u.text;log.scrollTop=log.scrollHeight;}});
        m.textContent=r.text;turns.push({role:'assistant',content:r.text});typeset(m);
        logChat({where:ctxWhere,sel:qPicked.slice(0,1500),q:q,a:r.text.slice(0,20000),tier:tier.value,page:location.pathname,turn:Math.ceil(turns.length/2)});
        // 1.5.0: 노트 기능(notes.js)이 답 아래에 [노트에 붙이기] 버튼을 달 수 있게 알림 (노트가 꺼져 있으면 듣는 쪽이 없음)
        try{document.dispatchEvent(new CustomEvent('board:qa',{detail:{el:m,where:ctxWhere,sel:qPicked,q:q,a:r.text}}));}catch(e){}}
      catch(err){m.textContent=(err.text||'')+(err.code==='cancelled'?'\n(멈춤)':'\n(답을 받지 못했습니다: '+err.code+')');turns.pop();
        if(err.code==='not_granted'){fab.hidden=true;box.hidden=true;}}
      ctl=null;stop.hidden=true;});
  });
})();
