(() => {
  'use strict';
  const $ = (q, root = document) => root.querySelector(q);
  const $$ = (q, root = document) => [...root.querySelectorAll(q)];
  const money = value => 'NT$ ' + Number(value).toLocaleString('zh-TW');
  const toast = (message, error = false, cartLink = false) => {
    const el = document.createElement('div'); el.className = 'toast' + (error ? ' toast--error' : '');
    const text = document.createElement('span'); text.textContent = message; el.append(text);
    if (cartLink) { const link = document.createElement('a'); link.href = '/orders/cart/'; link.textContent = '查看購物車'; el.append(link); }
    $('#toastContainer').append(el); setTimeout(() => el.remove(), 5500);
  };
  const post = async (url, data = {}) => {
    const response = await fetch(url, { method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': $('#csrf-token input')?.value || '', 'Content-Type': 'application/json'}, body: JSON.stringify(data) });
    let result;
    try { result = await response.json(); } catch { throw new Error('目前無法完成操作，請重新整理後再試。'); }
    if (!response.ok || !result.success) throw new Error(result.message || '操作未成功，請稍後再試。');
    $$('.cart-badge').forEach(el => el.textContent = result.cart_count); return result;
  };
  const mobile = () => matchMedia('(max-width: 960px)').matches;
  const menu = $('#menuToggle'), sidebar = $('#sidebar'), overlay = $('#sidebarOverlay');
  const closeMenu = () => { sidebar.classList.remove('is-open'); overlay.hidden = true; menu.setAttribute('aria-expanded','false'); menu.setAttribute('aria-label','開啟選單'); document.body.style.overflow = ''; if(mobile()) sidebar.inert = true; };
  const openMenu = () => { sidebar.inert = false; sidebar.classList.add('is-open'); overlay.hidden = false; menu.setAttribute('aria-expanded','true'); menu.setAttribute('aria-label','關閉選單'); document.body.style.overflow = 'hidden'; sidebar.querySelector('a')?.focus(); };
  menu?.addEventListener('click', () => {
    if (mobile()) sidebar.classList.contains('is-open') ? closeMenu() : openMenu();
    else { const collapsed = document.body.classList.toggle('nav-collapsed'); sidebar.inert = collapsed; menu.setAttribute('aria-expanded',String(!collapsed)); }
  });
  overlay?.addEventListener('click', () => { closeMenu(); menu.focus(); });
  const syncMenu = () => { closeMenu(); if(!mobile()) { sidebar.inert = document.body.classList.contains('nav-collapsed'); menu.setAttribute('aria-expanded',String(!sidebar.inert)); } };
  window.addEventListener('resize', syncMenu); syncMenu();
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { if(sidebar.classList.contains('is-open')){closeMenu();menu.focus();} $('#memberMenu').hidden = true; $('#memberToggle').setAttribute('aria-expanded','false'); }
    if(e.key === 'Tab' && mobile() && sidebar.classList.contains('is-open')){
      const focusable = $$('a,button',sidebar), first=focusable[0],last=focusable.at(-1);
      if(e.shiftKey && document.activeElement===first){e.preventDefault();last.focus();}
      else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  $('#memberToggle')?.addEventListener('click', () => { const panel=$('#memberMenu');panel.hidden=!panel.hidden;$('#memberToggle').setAttribute('aria-expanded',String(!panel.hidden)); });
  document.addEventListener('click', e => { if(!e.target.closest('.member-dropdown')){$('#memberMenu').hidden=true;$('#memberToggle').setAttribute('aria-expanded','false');} });
  $$('.alert-close').forEach(button => button.addEventListener('click', () => button.closest('.alert').remove()));
  const slides=$$('.hero-slide'), dots=$('.hero-dots'); let current=0;
  const showSlide = index => {
    current=(index+slides.length)%slides.length;
    slides.forEach((slide,i)=>{slide.hidden=i!==current;slide.classList.toggle('is-active',i===current);});
    $$('button',dots).forEach((dot,i)=>{dot.classList.toggle('is-active',i===current);dot.setAttribute('aria-pressed',String(i===current));});
    $('.hero-count').textContent=String(current+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0');
  };
  if(slides.length){
    slides.forEach((_,i)=>{const dot=document.createElement('button');dot.type='button';dot.setAttribute('aria-label','第 '+(i+1)+' 張廣告');dot.addEventListener('click',()=>showSlide(i));dots.append(dot);});
    $('.slide-prev').addEventListener('click',()=>showSlide(current-1));$('.slide-next').addEventListener('click',()=>showSlide(current+1));showSlide(0);
    $('.hero').addEventListener('keydown',e=>{if(e.key==='ArrowRight')showSlide(current+1);if(e.key==='ArrowLeft')showSlide(current-1);});
    let startX=0;$('.hero').addEventListener('touchstart',e=>startX=e.changedTouches[0].clientX,{passive:true});
    $('.hero').addEventListener('touchend',e=>{const distance=e.changedTouches[0].clientX-startX;if(Math.abs(distance)>55)showSlide(current+(distance<0?1:-1));},{passive:true});
  }
  $$('.add-cart').forEach(button => button.addEventListener('click', async () => {
    if(button.disabled)return;
    const quantity=$('#productQuantity')?.value || 1;button.disabled=true;
    try{const result=await post(button.dataset.url,{quantity});toast(result.message,false,true);}
    catch(error){toast(error.message,true);}
    finally{button.disabled=false;}
  }));
  $$('[data-qty-step]').forEach(button => button.addEventListener('click', () => {
    const input=$('#productQuantity'), next=Number(input.value)+Number(button.dataset.qtyStep);
    input.value=Math.max(1,Math.min(Number(input.max),next));
  }));
  $$('[data-gallery-image]').forEach(button=>button.addEventListener('click',()=>$('#mainImage').src=button.dataset.galleryImage));
  const updateSummary=result=>{ $$('[data-summary]').forEach(el=>{el.textContent=el.dataset.summary==='shipping'&&Number(result.shipping)===0?'免運費':money(result[el.dataset.summary]);}); };
  $$('.cart-item').forEach(row=>{
    const input=$('input',row); if(!input)return; let previous=input.value;
    const update=async quantity=>{
      row.classList.add('loading');
      try{const result=await post(row.dataset.updateUrl,{quantity});input.value=quantity;previous=String(quantity);$('[data-item-total]',row).textContent=money(result.item_subtotal);updateSummary(result);}
      catch(error){input.value=previous;toast(error.message,true);}
      finally{row.classList.remove('loading');}
    };
    $$('[data-cart-step]',row).forEach(button=>button.addEventListener('click',()=>{const next=Number(input.value)+Number(button.dataset.cartStep);if(next>=1)update(next);}));
    input.addEventListener('change',()=>update(input.value));
    $('[data-remove]',row)?.addEventListener('click',async()=>{row.classList.add('loading');try{const result=await post(row.dataset.removeUrl);row.remove();updateSummary(result);if(!$$('.cart-item').length)location.reload();}catch(error){toast(error.message,true);row.classList.remove('loading');}});
  });
  $$('form[data-single-submit]').forEach(form=>form.addEventListener('submit',()=>{const button=$('button[type=submit]',form);if(button){button.disabled=true;button.textContent='正在送出…';}}));
  window.addEventListener('pageshow',()=>$$('form[data-single-submit] button[type=submit]').forEach(button=>{button.disabled=false;button.textContent=button.dataset.label||'送出';}));
})();

// Preview selected product/banner images locally, before uploading.
(() => {
  const input = document.querySelector('input[type="file"][name="image"]');
  const preview = document.querySelector('[data-image-preview]');
  if (!input || !preview) return;
  let localUrl;
  input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    if (localUrl) URL.revokeObjectURL(localUrl);
    localUrl = URL.createObjectURL(file);
    preview.src = localUrl;
    preview.hidden = false;
  });
})();
