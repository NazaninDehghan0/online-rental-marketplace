/* منطق سایت دارینو: ارتباط با API (بک‌اند)، نمایش کالاها، حساب کاربری و درخواست اجاره */
const $=s=>document.querySelector(s),fa=n=>Number(n).toLocaleString('fa-IR'),money=n=>fa(n)+' تومان';
const rt=i=>i.r?fa(i.r):'جدید',norm=v=>v.trim().replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store={get(k){try{return localStorage.getItem(k)||''}catch(e){return ''}},set(k,v){try{v?localStorage.setItem(k,v):localStorage.removeItem(k)}catch(e){}}};
let cat='all',favs=new Set(),reqs=[],user=null,promo=null,onlyFav=false,token=store.get('d_token'),rq=0,tm;

async function api(path,o={}){
  const h={'Content-Type':'application/json'};if(token)h.Authorization='Bearer '+token;
  let r;try{r=await fetch('/api'+path,{method:o.method||'GET',headers:h,body:o.body?JSON.stringify(o.body):undefined})}
  catch(e){throw new Error('ارتباط با سرور برقرار نشد. مطمئن شو server.py اجرا شده و سایت را از http://localhost:8000 باز کرده‌ای.')}
  const d=await r.json().catch(()=>({}));
  if(!r.ok){if(r.status===401&&token)resetSession();throw new Error(d.error||'خطای سرور')}
  return d;
}
function resetSession(){token='';user=null;favs=new Set();reqs=[];promo=null;store.set('d_token','');badges();renderDrawer()}
function toast(t){const e=$('#toast');e.textContent=t;e.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>e.classList.remove('show'),2600)}
function badges(){$('#favN').textContent=fa(favs.size);$('#cartN').textContent=fa(reqs.length);$('#favBtn').firstChild.textContent=favs.size?'♥':'♡';$('#userBtn').textContent=user?'👤 '+user.name.split(' ')[0]:'ورود / ثبت‌نام'}
async function loadUserData(){
  try{favs=new Set((await api('/favorites')).ids);reqs=(await api('/requests?status=draft')).requests}catch(e){}
  badges();renderDrawer();
}
function renderCats(){$('#cats').innerHTML=CATS.map(c=>`<button class="cat ${c.k===cat?'on':''}" data-k="${c.k}"><span class="i">${c.i}</span><b>${c.n}</b></button>`).join('')}
async function renderGrid(){
  const my=++rq,p=new URLSearchParams({cat,q:$('#q').value.trim(),sort:$('#sort').value});if(onlyFav)p.set('fav','1');
  let l;try{l=(await api('/items?'+p)).items}catch(e){if(my===rq)$('#grid').innerHTML=`<div class="empty">${esc(e.message)}</div>`;return}
  if(my!==rq)return;
  $('#grid').innerHTML=l.length?l.map(i=>`<article class="glass p" data-id="${i.id}"><div class="pic">${i.e}<button class="heart ${favs.has(i.id)?'on':''}" data-h="${i.id}" aria-label="علاقه‌مندی">${favs.has(i.id)?'♥':'♡'}</button></div><h3>${esc(i.n)}</h3><div class="meta"><span>📍 ${esc(i.city)}</span><span>⭐ ${rt(i)}</span></div><div class="price"><div><b>${money(i.p)}</b> <span>/ روز</span></div><button class="btn mini">مشاهده و اجاره</button></div></article>`).join(''):'<div class="empty">کالایی با این مشخصات پیدا نشد. عبارت دیگری را جست‌وجو کن یا دسته‌بندی را عوض کن.</div>';
}
async function openItem(id){
  let i;try{i=(await api('/items/'+id)).item}catch(e){return toast(e.message)}
  const t=new Date().toISOString().slice(0,10);
  $('#modal').innerHTML=`<button class="x" data-close aria-label="بستن">✕</button><div class="mgrid"><div class="pic">${i.e}</div><div><h3 style="font-size:1.3rem">${esc(i.n)}</h3><p class="meta" style="justify-content:flex-start;gap:14px"><span>📍 ${esc(i.city)}</span><span>⭐ ${rt(i)}</span><span>👤 ${esc(i.o)}</span></p><p style="color:var(--mut);margin-top:8px">${esc(i.d)}</p><div class="specs">${i.s.map(x=>`<div>${esc(x)}</div>`).join('')}</div></div></div>
  <h3 style="margin-top:18px">ثبت درخواست اجاره</h3>
  <div class="row2"><div><label for="fn">نام و نام خانوادگی</label><input id="fn" type="text" autocomplete="name" value="${user?esc(user.name):''}"></div><div><label for="fp">شماره تماس</label><input id="fp" type="tel" inputmode="numeric" placeholder="۰۹۱۲۳۴۵۶۷۸۹" value="${user?esc(user.phone):''}"></div></div>
  <div class="row2"><div><label for="fd">تاریخ شروع</label><input id="fd" type="date" min="${t}" value="${t}"></div><div><label for="fk">تعداد روز</label><input id="fk" type="number" min="1" max="30" value="1"></div></div>
  <div class="sum"><span>هزینه اجاره (<span id="dd">۱</span> روز)</span><b id="tt">${money(i.p)}</b></div>
  <div class="err" id="er"></div>
  <button class="btn" id="add" data-id="${i.id}">افزودن به درخواست‌ها</button>
  <hr style="border:0;border-top:1px solid var(--line);margin:18px 0"><label for="msg">پیام به صاحب کالا (${esc(i.o)})</label><textarea id="msg" placeholder="مثلاً: آیا کالا برای آخر هفته آزاد است؟"></textarea><button class="btn ghost mini" id="smsg" data-id="${i.id}" data-o="${esc(i.o)}" style="margin-top:8px">ارسال پیام</button>`;
  $('#ov').classList.add('show');
  $('#fk').oninput=()=>{const k=Math.max(1,Math.min(30,+$('#fk').value||1));$('#dd').textContent=fa(k);$('#tt').textContent=money(k*i.p)};
}
function openAuth(m){
  const M=$('#modal'),X='<button class="x" data-close aria-label="بستن">✕</button>';
  if(user){M.innerHTML=X+`<h3>سلام ${esc(user.name)} 👋</h3><p style="color:var(--mut);margin:8px 0 16px">شماره تماس: ${esc(user.phone)}<br>${fa(reqs.length)} درخواست اجاره در لیست داری و ${fa(user.items||0)} کالا ثبت کرده‌ای.</p><button class="btn" id="out">خروج از حساب</button>`;$('#ov').classList.add('show');return}
  const s=m==='in';
  M.innerHTML=X+`<h3 style="margin-bottom:12px">به دارینو خوش آمدی</h3><div class="tabs"><button data-tab="up" class="${s?'':'on'}">ثبت‌نام</button><button data-tab="in" class="${s?'on':''}">ورود</button></div>${s?'':'<label for="an">نام و نام خانوادگی</label><input id="an" type="text" autocomplete="name">'}<label for="ap">شماره تماس</label><input id="ap" type="tel" inputmode="numeric" placeholder="۰۹۱۲۳۴۵۶۷۸۹"><label for="aw">رمز عبور (حداقل ۶ نویسه)</label><input id="aw" type="password"><div class="err" id="aer"></div><button class="btn" id="asub" data-m="${m}">${s?'ورود':'ایجاد حساب'}</button><p class="note" style="margin-top:10px">رمز عبور به‌صورت هش‌شده در پایگاه داده ذخیره می‌شود؛ پرداخت واقعی وجود ندارد.</p>`;
  $('#ov').classList.add('show');
}
async function authSubmit(m){
  const p=norm($('#ap').value),w=$('#aw').value,er=$('#aer'),n=m==='up'?$('#an').value.trim():'';
  if(m==='up'&&n.length<3)return er.textContent='نام و نام خانوادگی را کامل وارد کن.';
  if(!/^09\d{9}$/.test(p))return er.textContent='شماره تماس باید ۱۱ رقم و با ۰۹ شروع شود.';
  if(w.length<6)return er.textContent='رمز عبور حداقل ۶ نویسه باشد.';
  try{const d=await api(m==='up'?'/auth/register':'/auth/login',{method:'POST',body:{name:n,phone:p,password:w}});
    token=d.token;user=d.user;store.set('d_token',token);$('#ov').classList.remove('show');
    await loadUserData();renderGrid();toast('خوش آمدی '+user.name.split(' ')[0]);
  }catch(e){er.textContent=e.message}
}
async function addReq(id){
  if(!user){openAuth('in');return toast('برای ثبت درخواست ابتدا وارد حساب شو')}
  const n=$('#fn').value.trim(),p=norm($('#fp').value),d=$('#fd').value,k=Math.max(1,Math.min(30,+$('#fk').value||1)),er=$('#er');
  if(n.length<3)return er.textContent='نام و نام خانوادگی را کامل وارد کن.';
  if(!/^09\d{9}$/.test(p))return er.textContent='شماره تماس باید ۱۱ رقم و با ۰۹ شروع شود.';
  if(!d)return er.textContent='تاریخ شروع اجاره را انتخاب کن.';
  try{await api('/requests',{method:'POST',body:{item_id:+id,start_date:d,days:k,contact_name:n,contact_phone:p}});
    await loadUserData();$('#ov').classList.remove('show');toast('درخواست اجاره به لیست اضافه شد');
  }catch(e){er.textContent=e.message}
}
function renderDrawer(){
  $('#dl').innerHTML=reqs.length?reqs.map(r=>`<div class="ri"><span class="e">${r.e}</span><div><b>${esc(r.n)}</b><br>${new Date(r.d).toLocaleDateString('fa-IR')} · ${fa(r.k)} روز<br><span style="color:var(--acc)">${money(r.t)}</span></div><button data-del="${r.id}" aria-label="حذف">🗑️</button></div>`).join(''):'<div class="empty">هنوز درخواستی ثبت نکرده‌ای. از بخش کالاها یک مورد را انتخاب کن.</div>';
  const sub=reqs.reduce((a,r)=>a+r.t,0),dis=promo?Math.round(sub*promo.percent/100):0;
  $('#sub').textContent=money(sub);$('#dis').textContent=dis?'− '+money(dis):money(0);$('#tot').textContent=money(sub-dis);
}
document.addEventListener('click',async e=>{
  const t=e.target;let h=t.closest('[data-h]');
  try{
  if(h){e.stopPropagation();if(!user){openAuth('in');return toast('برای افزودن به علاقه‌مندی‌ها وارد شو')}
    const id=+h.dataset.h,d=await api('/favorites/'+id,{method:'POST'});d.on?favs.add(id):favs.delete(id);badges();renderGrid();return}
  const c=t.closest('.cat');if(c){cat=c.dataset.k;renderCats();renderGrid();return}
  const p=t.closest('.p');if(p){openItem(p.dataset.id);return}
  if(t.closest('[data-close]')||t===$('#ov')){$('#ov').classList.remove('show');return}
  if(t.id==='add'){await addReq(t.dataset.id);return}
  const tb=t.closest('[data-tab]');if(tb){openAuth(tb.dataset.tab);return}
  if(t.id==='asub'){await authSubmit(t.dataset.m);return}
  if(t.id==='out'){try{await api('/auth/logout',{method:'POST'})}catch(x){}resetSession();$('#ov').classList.remove('show');renderGrid();toast('از حساب خارج شدی');return}
  if(t.id==='pa'){try{promo=await api('/promo',{method:'POST',body:{code:$('#pc').value}});renderDrawer();toast('کد تخفیف '+fa(promo.percent)+'٪ اعمال شد')}catch(x){promo=null;renderDrawer();toast(x.message)}return}
  if(t.id==='smsg'){if(!user){openAuth('in');return toast('برای ارسال پیام ابتدا وارد حساب شو')}
    const d=await api('/items/'+t.dataset.id+'/messages',{method:'POST',body:{text:$('#msg').value}});$('#msg').value='';toast('پیام برای '+d.to+' ارسال شد');return}
  const d=t.closest('[data-del]');if(d){await api('/requests/'+d.dataset.del,{method:'DELETE'});await loadUserData();return}
  }catch(x){toast(x.message)}
});
$('#cartBtn').onclick=()=>{renderDrawer();$('#drawer').classList.add('show')};
$('#closeD').onclick=()=>$('#drawer').classList.remove('show');
$('#favBtn').onclick=()=>{
  if(!user){openAuth('in');return toast('برای دیدن علاقه‌مندی‌ها وارد شو')}
  if(!onlyFav&&!favs.size)return toast('هنوز کالایی را به علاقه‌مندی‌ها اضافه نکرده‌ای');
  onlyFav=!onlyFav;$('#favBtn').style.borderColor=onlyFav?'var(--acc)':'';cat='all';$('#q').value='';renderCats();renderGrid();
  toast(onlyFav?'فقط علاقه‌مندی‌ها نمایش داده می‌شود':'همه کالاها نمایش داده می‌شود');$('#browse').scrollIntoView({behavior:'smooth'});
};
$('#favB').onclick=()=>$('#favBtn').click();
$('#userBtn').onclick=$('#userB').onclick=()=>openAuth('up');
$('#lsend').onclick=async()=>{
  const er=$('#ler');
  if(!user){openAuth('up');return toast('برای ثبت کالا ابتدا ثبت‌نام کن یا وارد شو')}
  if($('#ln').value.trim().length<3)return er.textContent='نام کالا را وارد کن.';
  if(!(+$('#lp').value>=10000))return er.textContent='قیمت روزانه را وارد کن (حداقل ۱۰٬۰۰۰ تومان).';
  if($('#lcity').value.trim().length<2)return er.textContent='شهر را وارد کن.';
  try{await api('/items',{method:'POST',body:{name:$('#ln').value,category:$('#lc').value,price:+$('#lp').value,city:$('#lcity').value,description:$('#ld').value}});
    er.textContent='';['ln','lp','lcity','ld'].forEach(x=>$('#'+x).value='');user.items=(user.items||0)+1;cat='all';onlyFav=false;renderCats();renderGrid();
    toast('کالای تو در فهرست قرار گرفت');$('#browse').scrollIntoView({behavior:'smooth'});
  }catch(e){er.textContent=e.message}
};
$('#send').onclick=async()=>{
  if(!reqs.length)return toast('ابتدا یک کالا را انتخاب کن');
  try{await api('/requests/submit',{method:'POST',body:{promo:promo?promo.code:''}});reqs=[];promo=null;$('#pc').value='';badges();renderDrawer();$('#drawer').classList.remove('show');toast('درخواست‌ها ثبت شد؛ صاحب کالا با شما تماس می‌گیرد')}
  catch(e){toast(e.message)}
};
$('#q').oninput=()=>{clearTimeout(tm);tm=setTimeout(renderGrid,250)};$('#sort').onchange=renderGrid;
document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('#ov').classList.remove('show');$('#drawer').classList.remove('show')}});
$('#faq').innerHTML=FAQ.map((f,i)=>`<details class="glass" ${i===0?'open':''}><summary>${f[0]}</summary><p>${f[1]}</p></details>`).join('');
(async()=>{
  renderCats();badges();renderDrawer();
  if(token){try{user=(await api('/auth/me')).user;await loadUserData()}catch(e){}}
  badges();renderGrid();
})();
