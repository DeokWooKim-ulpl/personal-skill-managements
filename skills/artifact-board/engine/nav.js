(function(){
  function sel(btns,on){btns.forEach(function(b){b.setAttribute('aria-selected',b===on?'true':'false');});}
  function showTop(tok,sub){var tb=[].slice.call(document.querySelectorAll('nav.top button'));
    var t=tb.filter(function(b){return b.dataset.t===tok;})[0]||tb[0];sel(tb,t);
    tb.forEach(function(b){document.getElementById('top-'+b.dataset.t).hidden=b!==t;});
    var pane=document.getElementById('top-'+t.dataset.t);
    if(pane.dataset.src&&!pane.dataset.loaded){var ph=pane.querySelector('.lazy');
      if(!pane.dataset.loading){pane.dataset.loading='1';
        fetch(pane.dataset.src).then(function(r){if(!r.ok)throw r.status;return r.text();}).then(function(h){
          var box=document.createElement('div');box.innerHTML=h;ph.replaceWith.apply(ph,[].slice.call(box.childNodes));pane.dataset.loaded='1';
          if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise([pane]).catch(function(){});
          document.dispatchEvent(new CustomEvent('board:pane',{detail:pane}));
          var cur=document.querySelector('nav.top button[aria-selected="true"]');if(cur&&cur.dataset.t===t.dataset.t)showTop(t.dataset.t,sub);})
        .catch(function(e){delete pane.dataset.loading;if(ph)ph.textContent='이 탭을 불러오지 못했습니다 ('+e+'). 새로 고침해 보세요.';});}
      var sb0=[].slice.call(pane.querySelectorAll('nav.sub button'));var s0=sb0.filter(function(b){return b.dataset.s===sub;})[0]||sb0[0];if(s0)sel(sb0,s0);
      try{history.replaceState(null,'','#'+t.dataset.t+(s0?'-'+s0.dataset.s:''));}catch(e){}return;}
    var sb=[].slice.call(pane.querySelectorAll('nav.sub button'));
    var s=sb.filter(function(b){return b.dataset.s===sub;})[0]||sb[0];if(s){sel(sb,s);
      sb.forEach(function(b){document.getElementById('sub-'+t.dataset.t+'-'+b.dataset.s).hidden=b!==s;});}
    try{history.replaceState(null,'','#'+t.dataset.t+(s?'-'+s.dataset.s:''));}catch(e){}}
  // 1.5.0: 본문 안 '#큰탭-작은탭' 링크(예: 설계서 표의 #design-d01)를 누르면 그 탭으로 감
  document.addEventListener('click',function(e){var a=e.target.closest('a[href^="#"]');if(!a||e.defaultPrevented)return;
    var h=a.getAttribute('href').slice(1),i=h.indexOf('-'),t=i<0?h:h.slice(0,i);
    if(t&&document.querySelector('nav.top button[data-t="'+t+'"]')){e.preventDefault();showTop(t,i<0?'':h.slice(i+1));window.scrollTo(0,0);}});
  document.addEventListener('click',function(e){var b=e.target.closest('nav button');if(!b)return;
    if(b.dataset.t){showTop(b.dataset.t);window.scrollTo(0,0);}else{var top=b.closest('[id^="top-"]').id.slice(4);showTop(top,b.dataset.s);}});
  if(document.querySelector('nav.top button')){var h=(location.hash||'').slice(1),i=h.indexOf('-');showTop(i<0?h:h.slice(0,i),i<0?'':h.slice(i+1));}
})();
