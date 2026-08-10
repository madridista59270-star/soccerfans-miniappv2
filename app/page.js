"use client";

import { useEffect, useMemo, useState } from "react";

const FALLBACK_PRODUCTS = [
  {id:1,name:"Real Madrid Domicile 26/27",team:"Real Madrid",cat:"Clubs",versions:{Fan:35,Player:45},emoji:"⚪",hot:true},
  {id:2,name:"Paris Domicile 26/27",team:"Paris",cat:"Clubs",versions:{Fan:35,Player:45},emoji:"🔵",hot:true},
  {id:3,name:"Barcelone Domicile 26/27",team:"Barcelone",cat:"Clubs",versions:{Fan:35,Player:45},emoji:"🔴"},
  {id:4,name:"France Domicile 2026",team:"France",cat:"Nations",versions:{Fan:35,Player:45},emoji:"🇫🇷",hot:true},
  {id:5,name:"Brésil Rétro 2002",team:"Brésil",cat:"Rétro",versions:{Rétro:50},emoji:"🇧🇷"},
  {id:6,name:"Argentine Domicile",team:"Argentine",cat:"Nations",versions:{Fan:35,Player:45},emoji:"🇦🇷"},
  {id:7,name:"Milan Rétro 06/07",team:"Milan",cat:"Rétro",versions:{Rétro:50},emoji:"🔴"},
  {id:8,name:"Kit Enfant France",team:"France",cat:"Enfant",versions:{Enfant:30},emoji:"🧒"}
];

const fmt = n => new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"}).format(n);

const getProductType = name => {
  const low=(name||"").toLowerCase();

  // Priorité : Short > Enfant > Rétro > Player > Fan
  if(/shorts?/i.test(low)) return "Short";
  if(/(kid|kids|child|children|youth|junior|enfant)/i.test(low)) return "Enfant";
  if(/(retro|rétro|vintage|classic)/i.test(low)) return "Rétro";
  if(/player/i.test(low)) return "Player";
  if(/fan/i.test(low)) return "Fan";
  return "";
};

function applyPricingRules(product){
  if(!product || typeof product!=="object") return product;

  const type=getProductType(product.name);
  if(type==="Short")  return {...product, versions:{Short:20}};
  if(type==="Enfant") return {...product, versions:{Enfant:30}};
  if(type==="Rétro")  return {...product, versions:{Rétro:50}};
  if(type==="Player") return {...product, versions:{Player:45}};
  if(type==="Fan")    return {...product, versions:{Fan:35}};

  return product;
}

function getProductImages(product){
  if(!product) return [];
  const all=[
    product.image,
    ...(Array.isArray(product.images)?product.images:[])
  ].filter(Boolean);
  return [...new Set(all)];
}

const LEAGUES = {
  "Ligue 1":["paris","psg","marseille","om ","lyon","monaco","lille","lens","rennes","nice"],
  "Premier League":["liverpool","arsenal","chelsea","manchester","tottenham","newcastle","aston villa","west ham"],
  "La Liga":["real madrid","barcelona","barcelone","atletico","atlético","sevilla","seville","valencia","betis"],
  "Serie A":["juventus","milan","inter","napoli","roma","lazio","atalanta","fiorentina"],
  "Bundesliga":["bayern","dortmund","leverkusen","leipzig","frankfurt","stuttgart","wolfsburg"]
};

export default function Home(){
  const [tg,setTg]=useState(null);
  const [user,setUser]=useState(null);
  const [query,setQuery]=useState("");
  const [cat,setCat]=useState("Tous");
  const [selected,setSelected]=useState(null);
  const [galleryIndex,setGalleryIndex]=useState(0);
  const [version,setVersion]=useState("");
  const [size,setSize]=useState("M");
  const [printing,setPrinting]=useState("");
  const [cart,setCart]=useState([]);
  const [favs,setFavs]=useState([]);
  const [screen,setScreen]=useState("shop");
  const [cartOpen,setCartOpen]=useState(false);
  const [promo,setPromo]=useState("");
  const [products,setProducts]=useState(()=>FALLBACK_PRODUCTS.map(applyPricingRules));
  const [activeLeague,setActiveLeague]=useState("");
  const [visibleCount,setVisibleCount]=useState(24);

  useEffect(()=>{
    const app=window.Telegram?.WebApp;
    if(app){
      app.ready(); app.expand();
      try{ app.setHeaderColor("#08090b"); app.setBackgroundColor("#08090b"); }catch{}
      setTg(app);
      setUser(app.initDataUnsafe?.user || null);
    }
    try{
      setCart(JSON.parse(localStorage.getItem("sf_cart_pro")||"[]"));
      setFavs(JSON.parse(localStorage.getItem("sf_favs")||"[]"));
    }catch{}
  },[]);

  useEffect(()=>{
    let cancelled=false;
    fetch("/products.json",{cache:"no-store"})
      .then(r=>{
        if(!r.ok) throw new Error(`products.json: ${r.status}`);
        return r.json();
      })
      .then(data=>{
        if(!cancelled && Array.isArray(data) && data.length){
          setProducts(data.map(applyPricingRules));
        }
      })
      .catch(err=>console.warn("Catalogue automatique indisponible, catalogue de secours utilisé.",err));
    return ()=>{cancelled=true};
  },[]);

  useEffect(()=>{localStorage.setItem("sf_cart_pro",JSON.stringify(cart))},[cart]);
  useEffect(()=>{localStorage.setItem("sf_favs",JSON.stringify(favs))},[favs]);

  const filtered=useMemo(()=>products.filter(p=>{
    const okCat=cat==="Tous"||p.cat===cat;
    const q=query.toLowerCase().trim();
    const hay=(`${p.name||""} ${p.team||""} ${p.cat||""}`).toLowerCase();
    const okQ=!q||hay.includes(q);
    const keys=activeLeague ? (LEAGUES[activeLeague]||[]) : [];
    const okLeague=!activeLeague||keys.some(k=>hay.includes(k));
    return okCat&&okQ&&okLeague;
  }),[cat,query,products,activeLeague]);

  const displayedProducts=filtered.slice(0,visibleCount);

  useEffect(()=>{ setVisibleCount(24); },[cat,query,activeLeague]);

  function jumpToProducts(nextCat="Tous", nextQuery="", nextLeague=""){
    setCat(nextCat);
    setQuery(nextQuery);
    setActiveLeague(nextLeague);
    setVisibleCount(24);
    setTimeout(()=>document.getElementById("products")?.scrollIntoView({behavior:"smooth"}),60);
  }

  const subtotal=cart.reduce((s,x)=>s+x.price*x.qty,0);
  const discount=promo.trim().toUpperCase()==="WELCOME10"?subtotal*.10:0;
  const shipping=subtotal===0?0:(subtotal>=100?0:5.90);
  const total=Math.max(0,subtotal-discount+shipping);

  function openProduct(p){
    const fixed=applyPricingRules(p);
    setSelected(fixed);
    setGalleryIndex(0);
    setVersion(Object.keys(fixed.versions||{Fan:35})[0]);
    setSize("M"); setPrinting("");
    try{tg?.HapticFeedback?.impactOccurred("light")}catch{}
  }
  function add(){
    const fixed=applyPricingRules(selected);
    const price=(fixed.versions?.[version]??35)+(printing.trim()?3:0);
    setCart(c=>[...c,{key:crypto.randomUUID?.()||Date.now(),id:fixed.id,name:fixed.name,emoji:fixed.emoji,image:fixed.image||"",version,size,printing:printing.trim()||"Aucun",price,qty:1}]);
    setSelected(null);
    try{tg?.HapticFeedback?.notificationOccurred("success")}catch{}
  }
  function checkout(){
    if(!cart.length)return;
    const payload={action:"checkout",customer:user?{id:user.id,first_name:user.first_name,username:user.username}:null,items:cart,subtotal,discount,shipping,total};
    // For production, send to your HTTPS backend and validate Telegram initData server-side.
    // Keyboard-button Mini Apps can also use tg.sendData().
    if(tg?.sendData) tg.sendData(JSON.stringify(payload).slice(0,4000));
    else alert("Mode démonstration : commande prête.");
  }

  function Shop(){
    return <>
      <section className="sfBannerWrap">{/* TOP BANNER: KEEP */}
        <button
          className="sfBannerButton"
          onClick={()=>document.getElementById("products")?.scrollIntoView({behavior:"smooth"})}
          aria-label="Découvrir la collection Soccer Fans"
        >
          <img
            src="/banner-home.png"
            alt="Soccer Fans - Nouvelle saison 2026/27"
            className="sfBannerImage"
          />
        </button>
      </section>

      <section className="sfTrustGrid" aria-label="Nos garanties">
        <div className="sfTrustCard"><span>🚚</span><strong>7 à 14 jours</strong><small>Livraison suivie</small></div>
        <div className="sfTrustCard"><span>🔒</span><strong>Sécurisé</strong><small>Paiement</small></div>
        <div className="sfTrustCard"><span>🎽</span><strong>Personnalisé</strong><small>Flocage</small></div>
        <div className="sfTrustCard"><span>💬</span><strong>7j/7</strong><small>Support</small></div>
      </section>

      <div className="promoRow">
        <span className="promoRowIcon">🚚</span>
        <span>Livraison offerte dès 100 €</span>
        <span className="promoDot">•</span>
        <span>Code <b>WELCOME10</b></span>
      </div>

      <div className="searchBarWrap">
        <div className="searchBar">
          <span className="searchIcon">⌕</span>
          <input value={query} onChange={e=>{setQuery(e.target.value);setActiveLeague("");}} placeholder="Rechercher un club, un pays, un maillot..."/>
          <button className="filterBtn" type="button" aria-label="Filtres">☰</button>
        </div>
      </div>

      <div className="chips chipsPremium">
        {["Tous","Clubs","Nations","Rétro","Enfant"].map(x=><button key={x} className={"chip "+(cat===x?"on":"")} onClick={()=>{setCat(x);setActiveLeague("");setQuery("");}}>{x}</button>)}
      </div>

      <section className="sfExplore" aria-label="Collections Soccer Fans">
        <div className="sfExploreHead">
          <div><div className="kicker">Collections</div><h2>Choisis ton univers</h2></div>
          <span>2026/27</span>
        </div>

        <div className="sfNationPanel">
          <div className="sfPanelTitle"><span>🌍</span><b>NATIONS <em>2026</em></b></div>
          <div className="sfNationGrid">
            {[
              ["🇫🇷","France","france"],
              ["🇧🇷","Brésil","br"],
              ["🇦🇷","Argentine","argentine"],
              ["🇧🇪","Belgique","belg"]
            ].map(([flag,label,q])=>
              <button key={label} className="sfNationCard" onClick={()=>jumpToProducts("Nations",q,"")}>
                <span>{flag}</span><strong>{label}</strong>
              </button>
            )}
          </div>
        </div>

        <div className="sfLeaguePanel">
          <div className="sfPanelTitle"><span>🏆</span><b>CLUBS & CHAMPIONNATS</b></div>
          <div className="sfLeagueGrid">
            {[
              ["L1","Ligue 1"],
              ["PL","Premier League"],
              ["LIGA","La Liga"],
              ["A","Serie A"],
              ["BL","Bundesliga"]
            ].map(([mark,label])=>
              <button key={label} className={"sfLeagueCard "+(activeLeague===label?"on":"")} onClick={()=>jumpToProducts("Clubs","",label)}>
                <span>{mark}</span><strong>{label}</strong>
              </button>
            )}
          </div>
        </div>
      </section>

      <section id="products" className="section sectionPremium">
        <div className="section-head premiumHead"><div><div className="kicker">Catalogue</div><h2>Maillots populaires</h2></div><span>{filtered.length} produits</span></div>
        <div className="grid premiumGrid">
          {displayedProducts.map((p,index)=>{
            const minPrice=Math.min(...Object.values(p.versions||{Fan:35}));
            const flag = p.hot ? 'TOP' : (index % 2 ? 'NOUVEAU' : 'TOP');
            const versionKeys=Object.keys(p.versions||{Fan:35});
            const versionLabel = versionKeys.includes('Player') ? 'Player Version' : versionKeys.join(' • ');
            return <article className="card premiumCard" key={p.id}>
              <span className={"badge premiumBadge "+(flag==='NOUVEAU'?'alt':'')}>{flag}</span>
              <button className="heart premiumHeart" onClick={()=>setFavs(f=>f.includes(p.id)?f.filter(id=>id!==p.id):[...f,p.id])}>{favs.includes(p.id)?"♥":"♡"}</button>
              <div className={"card-img premiumVisual cat-"+(p.cat||"Clubs").toLowerCase()} onClick={()=>openProduct(p)}>
                <div className="productGlow"></div>
                {p.image
                  ? <img src={p.image} alt={p.name} className="productPhoto"/>
                  : <div className="productJersey">{p.emoji}</div>
                }
                <div className="productMark">{(p.team||"SF").slice(0,2).toUpperCase()}</div>
              </div>
              <div className="card-body premiumCardBody" onClick={()=>openProduct(p)}>
                <div className="card-title">{p.name}</div>
                <div className="meta">{versionLabel}</div>
                <div className="price">{fmt(minPrice)}</div>
              </div>
            </article>
          })}
        </div>

        {visibleCount<filtered.length&&
          <button className="loadMoreBtn" onClick={()=>setVisibleCount(v=>v+24)}>
            VOIR 24 PRODUITS DE PLUS <span>↓</span>
          </button>
        }

        <button className="collectionCta" onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}>
          <span className="collectionCtaIcon">🛡️</span>
          <span>VOIR TOUTE LA COLLECTION</span>
          <span className="collectionCtaArrow">→</span>
        </button>
      </section>
    </>
  }

  function Favorites(){
    const items=products.filter(p=>favs.includes(p.id));
    return <section className="section">
      <div className="section-head"><div><div className="kicker">Sélection</div><h2>Mes favoris</h2></div></div>
      {!items.length?<div className="empty">♡ Aucun favori pour le moment.</div>:
      <div className="grid">{items.map(p=><article className="card" key={p.id} onClick={()=>openProduct(p)}><div className="card-img">{p.image?<img src={p.image} alt={p.name} className="productPhoto"/>:p.emoji}</div><div className="card-body"><div className="card-title">{p.name}</div><div className="price">Dès {fmt(Math.min(...Object.values(p.versions||{Fan:35})))}</div></div></article>)}</div>}
    </section>
  }

  function Account(){
    return <section className="section">
      <div className="section-head"><div><div className="kicker">Telegram</div><h2>Mon compte</h2></div></div>
      <div className="profile">
        <strong>{user?`${user.first_name||""} ${user.last_name||""}`.trim():"Client Soccer Fans"}</strong>
        <p className="muted">{user?.username?`@${user.username}`:"Ouvre la boutique depuis Telegram pour activer ton profil automatiquement."}</p>
        <div className="sumline"><span>Favoris</span><b>{favs.length}</b></div>
        <div className="sumline"><span>Articles au panier</span><b>{cart.length}</b></div>
        <p className="tiny">En production, l'identité Telegram doit être vérifiée côté serveur avec initData avant de créer une session client.</p>
      </div>
    </section>
  }

  const selectedGallery=getProductImages(selected);
  const activeGalleryImage=selectedGallery.length
    ? selectedGallery[Math.min(galleryIndex,selectedGallery.length-1)]
    : "";

  return <main className="app">
    <style jsx global>{`
      .brand{
        display:flex;
        align-items:center;
        gap:12px;
      }
      .brandLogo{
        width:52px;
        height:52px;
        flex:0 0 52px;
        border-radius:50%;
        object-fit:cover;
        object-position:center;
        border:1px solid rgba(244,197,66,.55);
        box-shadow:0 0 18px rgba(244,197,66,.24);
        background:#08090b;
      }
      .cartTopButton{
        position:relative;
        width:54px;
        height:54px;
        flex:0 0 54px;
        display:grid;
        place-items:center;
        padding:0;
        border-radius:18px;
        border:1px solid rgba(244,197,66,.28);
        background:
          radial-gradient(circle at 35% 28%,rgba(244,197,66,.13),transparent 40%),
          #111318;
        color:#f4c542;
        box-shadow:
          inset 0 0 0 1px rgba(255,255,255,.015),
          0 10px 25px rgba(0,0,0,.22);
        cursor:pointer;
        -webkit-tap-highlight-color:transparent;
      }
      .cartTopButton:active{
        transform:scale(.96);
      }
      .cartTopIcon{
        width:28px;
        height:28px;
        display:block;
      }
      .cartTopIcon svg{
        display:block;
        width:100%;
        height:100%;
        filter:drop-shadow(0 0 7px rgba(244,197,66,.23));
      }
      .cartTopBadge{
        position:absolute;
        top:-5px;
        right:-5px;
        min-width:20px;
        height:20px;
        padding:0 5px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:999px;
        border:2px solid #08090b;
        background:#f4c542;
        color:#08090b;
        font-size:10px;
        font-weight:900;
        line-height:1;
        box-shadow:0 4px 12px rgba(244,197,66,.28);
      }
      .promoRow{
        display:flex;
        align-items:center;
        gap:10px;
        min-height:58px;
        padding:0 16px;
        border-radius:18px;
        border:1px solid rgba(244,197,66,.35);
        background:linear-gradient(180deg,#0f100f,#090909);
        color:#d8a92a;
        font-size:16px;
        font-weight:700;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.02),0 8px 28px rgba(0,0,0,.18);
        margin:12px 0 16px;
      }
      .promoRowIcon{font-size:20px}
      .promoRow b{color:#ffd15a}
      .promoDot{opacity:.55}

      .searchBarWrap{margin:0 0 14px}
      .searchBar{
        display:flex;
        align-items:center;
        gap:12px;
        min-height:64px;
        padding:0 14px 0 18px;
        border-radius:20px;
        border:1px solid rgba(244,197,66,.23);
        background:linear-gradient(180deg,#101115,#090a0d);
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.02);
      }
      .searchBar input{
        flex:1;
        min-width:0;
        background:transparent;
        border:0;
        outline:0;
        color:#fff;
        font-size:15px;
      }
      .searchBar input::placeholder{color:#5d616a}
      .searchIcon{
        font-size:22px;
        color:#a1a5ae;
        line-height:1;
      }
      .filterBtn{
        width:42px;
        height:42px;
        border-radius:14px;
        border:1px solid rgba(244,197,66,.22);
        background:#111318;
        color:#d8a92a;
        font-size:18px;
      }

      .chipsPremium{margin-bottom:22px !important}
      .chipsPremium .chip{
        min-height:46px !important;
        padding:0 24px !important;
        font-size:14px !important;
      }
      .chipsPremium .chip.on{
        box-shadow:0 0 0 1px rgba(255,209,90,.35),0 0 18px rgba(244,197,66,.18), inset 0 0 12px rgba(255,209,90,.08) !important;
      }

      .sectionPremium{padding-top:8px !important}
      .premiumHead{margin-bottom:18px !important}
      .premiumHead h2{font-size:32px !important;line-height:1.02 !important}
      .premiumHead > span{font-size:16px !important;color:#d8a92a !important;font-weight:700 !important}
      .premiumHead .kicker{font-size:12px !important;letter-spacing:.12em !important}
      .premiumHead h2::after{
        content:"";
        display:block;
        width:76px;
        height:4px;
        margin-top:12px;
        border-radius:999px;
        background:linear-gradient(90deg,#f4c542,#8a5d00);
      }

      .premiumGrid{gap:16px !important}
      .premiumCard{
        border-radius:24px !important;
        border:1px solid rgba(244,197,66,.45) !important;
        background:linear-gradient(180deg,#121212 0%,#090909 100%) !important;
        box-shadow:0 0 0 1px rgba(255,209,90,.08) inset, 0 12px 28px rgba(0,0,0,.28) !important;
      }
      .premiumVisual{
        min-height:220px !important;
        position:relative !important;
        overflow:hidden;
        display:flex !important;
        align-items:flex-end !important;
        justify-content:center !important;
        padding-bottom:18px;
        background:
          radial-gradient(circle at 50% 20%,rgba(255,209,90,.15),transparent 32%),
          radial-gradient(circle at 50% 100%,rgba(255,209,90,.09),transparent 58%),
          linear-gradient(180deg,#131415,#090909) !important;
      }
      .premiumVisual::before{
        content:"";
        position:absolute;
        inset:0;
        background:radial-gradient(circle at 14% 50%,rgba(244,197,66,.08),transparent 28%), radial-gradient(circle at 85% 22%,rgba(244,197,66,.08),transparent 22%);
        pointer-events:none;
      }
      .productGlow{
        position:absolute;
        width:190px;
        height:190px;
        border-radius:50%;
        background:radial-gradient(circle,rgba(244,197,66,.16),transparent 66%);
        filter:blur(4px);
        bottom:16px;
      }
      .productPhoto{
        position:relative;
        z-index:2;
        width:88%;
        height:205px;
        object-fit:contain;
        object-position:center bottom;
        filter:drop-shadow(0 14px 22px rgba(0,0,0,.48));
      }
      .productJersey{
        position:relative;
        z-index:2;
        font-size:104px !important;
        line-height:1;
        filter:drop-shadow(0 14px 22px rgba(0,0,0,.48));
      }
      .productMark{
        position:absolute;
        left:14px;
        bottom:16px;
        font-size:64px;
        font-weight:900;
        line-height:1;
        letter-spacing:-.05em;
        color:rgba(255,255,255,.06);
      }
      .premiumCardBody{
        padding:14px 16px 16px !important;
        border-top:1px solid rgba(244,197,66,.14);
      }
      .premiumCard .card-title{font-size:15px !important;line-height:1.22 !important}
      .premiumCard .meta{font-size:11px !important;color:#7f838d !important}
      .premiumCard .price{font-size:18px !important;color:#f4c542 !important}

      .premiumBadge{
        padding:7px 12px !important;
        border-radius:9px !important;
        font-size:12px !important;
        font-weight:900 !important;
        letter-spacing:.02em;
        color:#090909 !important;
        background:linear-gradient(135deg,#f8d45e,#d8a92a) !important;
        border:0 !important;
        text-transform:uppercase;
      }
      .premiumBadge.alt{background:linear-gradient(135deg,#ffe07b,#ebb537) !important}
      .premiumHeart{
        width:44px !important;
        height:44px !important;
        border:1px solid rgba(255,255,255,.18) !important;
        background:rgba(10,10,10,.74) !important;
        color:#fff !important;
        font-size:23px !important;
      }


      .sfExplore{
        margin:10px 0 24px;
        padding:18px 14px;
        border-radius:24px;
        border:1px solid rgba(244,197,66,.30);
        background:
          radial-gradient(circle at 50% 0%,rgba(244,197,66,.10),transparent 33%),
          linear-gradient(180deg,#111216,#090a0d);
        box-shadow:0 18px 40px rgba(0,0,0,.24);
      }
      .sfExploreHead{
        display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:14px;
      }
      .sfExploreHead h2{margin:4px 0 0;color:#fff;font-size:25px;line-height:1.05}
      .sfExploreHead>span{color:#f4c542;font-weight:950;font-size:17px}
      .sfNationPanel,.sfLeaguePanel{
        border:1px solid rgba(244,197,66,.18);
        border-radius:20px;
        background:rgba(7,8,10,.65);
        padding:13px;
      }
      .sfLeaguePanel{margin-top:12px}
      .sfPanelTitle{
        display:flex;align-items:center;justify-content:center;gap:8px;
        color:#fff;margin-bottom:12px;font-size:16px;letter-spacing:.03em;
      }
      .sfPanelTitle em{color:#f4c542;font-style:normal}
      .sfNationGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
      .sfNationCard{
        min-width:0;padding:11px 3px 9px;border-radius:15px;
        border:1px solid rgba(244,197,66,.20);
        background:linear-gradient(180deg,#15171c,#0c0d10);
        color:#fff;
      }
      .sfNationCard span{display:block;font-size:31px;line-height:1;margin-bottom:7px}
      .sfNationCard strong{display:block;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .sfNationCard:active{transform:scale(.97)}
      .sfLeagueGrid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px}
      .sfLeagueCard{
        min-width:0;min-height:86px;padding:9px 3px;border-radius:14px;
        border:1px solid rgba(244,197,66,.20);
        background:#111318;color:#fff;
      }
      .sfLeagueCard span{
        width:38px;height:38px;margin:0 auto 6px;display:grid;place-items:center;border-radius:12px;
        background:rgba(244,197,66,.09);color:#f4c542;font-size:13px;font-weight:950;
      }
      .sfLeagueCard strong{display:block;font-size:8px;line-height:1.1}
      .sfLeagueCard.on{
        border-color:#f4c542;
        box-shadow:0 0 0 2px rgba(244,197,66,.08),0 0 18px rgba(244,197,66,.12);
      }
      .loadMoreBtn{
        width:100%;min-height:58px;margin-top:18px;border-radius:18px;
        border:1px solid rgba(244,197,66,.35);
        background:#111318;color:#f4c542;font-size:13px;font-weight:950;letter-spacing:.04em;
      }
      .loadMoreBtn span{font-size:18px;margin-left:8px}
      .productHeroPhoto{width:100%;height:100%;object-fit:contain;display:block}
      .thumb img{width:100%;height:100%;object-fit:cover;display:block}
      @media (max-width:420px){
        .sfExplore{padding:14px 10px}
        .sfExploreHead h2{font-size:22px}
        .sfNationGrid{gap:6px}
        .sfNationCard span{font-size:27px}
        .sfNationCard strong{font-size:9px}
        .sfLeagueGrid{gap:5px}
        .sfLeagueCard{min-height:78px;padding:8px 2px}
        .sfLeagueCard span{width:34px;height:34px;font-size:11px}
        .sfLeagueCard strong{font-size:7px}
      }

      .collectionCta{
        width:100%;
        margin-top:18px;
        min-height:70px;
        border-radius:22px;
        border:1px solid rgba(244,197,66,.45);
        background:linear-gradient(180deg,#111,#090909);
        color:#d8a92a;
        display:flex;
        align-items:center;
        justify-content:center;
        gap:16px;
        font-size:18px;
        font-weight:900;
        letter-spacing:.02em;
        box-shadow:0 10px 26px rgba(0,0,0,.20), inset 0 0 0 1px rgba(255,255,255,.02);
      }
      .collectionCtaIcon{font-size:25px}
      .collectionCtaArrow{font-size:32px;line-height:1}

      .bottom{padding-bottom:max(8px, env(safe-area-inset-bottom)) !important}
      .nav{gap:4px !important}
      .nav b{font-size:24px !important;line-height:1}
      .nav.on::before{top:0 !important}

      @media (max-width:420px){
        .promoRow{font-size:14px;padding:0 13px;gap:8px}
        .searchBar{min-height:60px;padding:0 12px 0 15px}
        .chipsPremium .chip{padding:0 18px !important;min-height:44px !important}
        .premiumHead h2{font-size:27px !important}
        .premiumHead > span{font-size:14px !important}
        .premiumVisual{min-height:195px !important}
        .productJersey{font-size:88px !important}
  
      .sfExplore{
        margin:10px 0 24px;
        padding:18px 14px;
        border-radius:24px;
        border:1px solid rgba(244,197,66,.30);
        background:
          radial-gradient(circle at 50% 0%,rgba(244,197,66,.10),transparent 33%),
          linear-gradient(180deg,#111216,#090a0d);
        box-shadow:0 18px 40px rgba(0,0,0,.24);
      }
      .sfExploreHead{
        display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:14px;
      }
      .sfExploreHead h2{margin:4px 0 0;color:#fff;font-size:25px;line-height:1.05}
      .sfExploreHead>span{color:#f4c542;font-weight:950;font-size:17px}
      .sfNationPanel,.sfLeaguePanel{
        border:1px solid rgba(244,197,66,.18);
        border-radius:20px;
        background:rgba(7,8,10,.65);
        padding:13px;
      }
      .sfLeaguePanel{margin-top:12px}
      .sfPanelTitle{
        display:flex;align-items:center;justify-content:center;gap:8px;
        color:#fff;margin-bottom:12px;font-size:16px;letter-spacing:.03em;
      }
      .sfPanelTitle em{color:#f4c542;font-style:normal}
      .sfNationGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
      .sfNationCard{
        min-width:0;padding:11px 3px 9px;border-radius:15px;
        border:1px solid rgba(244,197,66,.20);
        background:linear-gradient(180deg,#15171c,#0c0d10);
        color:#fff;
      }
      .sfNationCard span{display:block;font-size:31px;line-height:1;margin-bottom:7px}
      .sfNationCard strong{display:block;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .sfNationCard:active{transform:scale(.97)}
      .sfLeagueGrid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px}
      .sfLeagueCard{
        min-width:0;min-height:86px;padding:9px 3px;border-radius:14px;
        border:1px solid rgba(244,197,66,.20);
        background:#111318;color:#fff;
      }
      .sfLeagueCard span{
        width:38px;height:38px;margin:0 auto 6px;display:grid;place-items:center;border-radius:12px;
        background:rgba(244,197,66,.09);color:#f4c542;font-size:13px;font-weight:950;
      }
      .sfLeagueCard strong{display:block;font-size:8px;line-height:1.1}
      .sfLeagueCard.on{
        border-color:#f4c542;
        box-shadow:0 0 0 2px rgba(244,197,66,.08),0 0 18px rgba(244,197,66,.12);
      }
      .loadMoreBtn{
        width:100%;min-height:58px;margin-top:18px;border-radius:18px;
        border:1px solid rgba(244,197,66,.35);
        background:#111318;color:#f4c542;font-size:13px;font-weight:950;letter-spacing:.04em;
      }
      .loadMoreBtn span{font-size:18px;margin-left:8px}
      .productHeroPhoto{width:100%;height:100%;object-fit:contain;display:block}
      .thumb img{width:100%;height:100%;object-fit:cover;display:block}
      @media (max-width:420px){
        .sfExplore{padding:14px 10px}
        .sfExploreHead h2{font-size:22px}
        .sfNationGrid{gap:6px}
        .sfNationCard span{font-size:27px}
        .sfNationCard strong{font-size:9px}
        .sfLeagueGrid{gap:5px}
        .sfLeagueCard{min-height:78px;padding:8px 2px}
        .sfLeagueCard span{width:34px;height:34px;font-size:11px}
        .sfLeagueCard strong{font-size:7px}
      }

      .collectionCta{font-size:16px;min-height:64px;gap:10px}
      }

      /* ===== SOCCER FANS — THÈME NOIR & OR POUR TOUT LE BAS DE PAGE ===== */
      .notice{
        margin:12px 0 16px !important;
        padding:14px 16px !important;
        border-radius:18px !important;
        border:1px solid rgba(244,197,66,.35) !important;
        background:
          radial-gradient(circle at 12% 20%,rgba(244,197,66,.10),transparent 36%),
          linear-gradient(135deg,#14120b,#0c0d10 55%,#111318) !important;
        color:#eee7d0 !important;
        box-shadow:0 12px 30px rgba(0,0,0,.20) !important;
      }
      .notice b{
        color:#f4c542 !important;
        font-weight:900 !important;
      }

      .search{
        margin:0 0 14px !important;
      }
      .search input,
      .input{
        width:100% !important;
        min-height:56px !important;
        border-radius:18px !important;
        border:1px solid rgba(244,197,66,.20) !important;
        background:#101116 !important;
        color:#fff !important;
        padding:0 17px !important;
        font-size:15px !important;
        outline:none !important;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.015) !important;
      }
      .search input::placeholder,
      .input::placeholder{
        color:#6f7179 !important;
      }
      .search input:focus,
      .input:focus{
        border-color:rgba(244,197,66,.75) !important;
        box-shadow:0 0 0 3px rgba(244,197,66,.09) !important;
      }

      .chips{
        display:flex !important;
        gap:9px !important;
        overflow-x:auto !important;
        padding:2px 0 8px !important;
        margin:0 0 14px !important;
        scrollbar-width:none !important;
      }
      .chips::-webkit-scrollbar{display:none !important}
      .chip{
        flex:0 0 auto !important;
        min-height:43px !important;
        padding:0 18px !important;
        border-radius:999px !important;
        border:1px solid rgba(244,197,66,.20) !important;
        background:#111318 !important;
        color:#b8bac2 !important;
        font-weight:800 !important;
        box-shadow:none !important;
      }
      .chip.on{
        border-color:#f4c542 !important;
        background:linear-gradient(135deg,#f7d45f,#c99414) !important;
        color:#08090b !important;
        box-shadow:0 8px 22px rgba(244,197,66,.17) !important;
      }

      .section{
        padding-top:14px !important;
      }
      .section-head{
        align-items:flex-end !important;
        margin-bottom:14px !important;
      }
      .section-head .kicker,
      .kicker{
        color:#d5a927 !important;
        letter-spacing:.20em !important;
        font-size:10px !important;
        font-weight:900 !important;
        text-transform:uppercase !important;
      }
      .section-head h2,
      .section h2{
        margin-top:5px !important;
        color:#fff !important;
        font-weight:950 !important;
        letter-spacing:-.025em !important;
      }
      .section-head > span{
        color:#8c8f98 !important;
        font-size:12px !important;
      }

      .grid{
        gap:12px !important;
      }
      .card{
        position:relative !important;
        overflow:hidden !important;
        border-radius:22px !important;
        border:1px solid rgba(244,197,66,.18) !important;
        background:
          linear-gradient(180deg,#15161a 0%,#0d0e11 100%) !important;
        box-shadow:0 12px 28px rgba(0,0,0,.22) !important;
      }
      .card:active{
        transform:scale(.988) !important;
      }
      .card-img{
        min-height:190px !important;
        display:grid !important;
        place-items:center !important;
        background:
          radial-gradient(circle at 50% 42%,rgba(244,197,66,.17),transparent 35%),
          radial-gradient(circle at 50% 100%,rgba(244,197,66,.08),transparent 55%),
          linear-gradient(180deg,#18191d,#101115) !important;
        color:#fff !important;
        font-size:70px !important;
        border-bottom:1px solid rgba(244,197,66,.12) !important;
      }
      .card-body{
        padding:13px 13px 15px !important;
        background:transparent !important;
      }
      .card-title{
        color:#fff !important;
        font-size:14px !important;
        font-weight:900 !important;
        line-height:1.25 !important;
      }
      .meta{
        margin-top:6px !important;
        color:#8c8f98 !important;
        font-size:11px !important;
      }
      .price{
        margin-top:8px !important;
        color:#f4c542 !important;
        font-size:15px !important;
        font-weight:950 !important;
      }
      .badge{
        top:11px !important;
        left:11px !important;
        border:1px solid rgba(244,197,66,.45) !important;
        background:rgba(10,10,10,.82) !important;
        color:#f4c542 !important;
        backdrop-filter:blur(8px) !important;
        box-shadow:0 5px 16px rgba(0,0,0,.22) !important;
      }
      .heart{
        top:10px !important;
        right:10px !important;
        width:40px !important;
        height:40px !important;
        border-radius:50% !important;
        border:1px solid rgba(244,197,66,.30) !important;
        background:rgba(10,10,10,.80) !important;
        color:#f4c542 !important;
        backdrop-filter:blur(8px) !important;
      }

      .bottom{
        border-top:1px solid rgba(244,197,66,.18) !important;
        background:rgba(9,10,13,.96) !important;
        box-shadow:0 -14px 35px rgba(0,0,0,.30) !important;
        backdrop-filter:blur(18px) !important;
      }
      .nav{
        position:relative !important;
        color:#747780 !important;
        transition:.18s ease !important;
      }
      .nav b{
        color:inherit !important;
        font-size:22px !important;
      }
      .nav.on{
        color:#f4c542 !important;
      }
      .nav.on::before{
        content:"" !important;
        position:absolute !important;
        top:4px !important;
        left:50% !important;
        width:26px !important;
        height:2px !important;
        border-radius:999px !important;
        transform:translateX(-50%) !important;
        background:#f4c542 !important;
        box-shadow:0 0 12px rgba(244,197,66,.65) !important;
      }

      .profile,
      .empty,
      .summary{
        border:1px solid rgba(244,197,66,.18) !important;
        background:linear-gradient(180deg,#141519,#0d0e11) !important;
        color:#fff !important;
        border-radius:20px !important;
      }
      .muted,.tiny{color:#858892 !important}
      .sumline{border-color:rgba(244,197,66,.10) !important}
      .sumline.total b{color:#f4c542 !important}

      .sheetback{
        background:rgba(0,0,0,.72) !important;
        backdrop-filter:blur(7px) !important;
      }
      .sheet{
        border-top:1px solid rgba(244,197,66,.28) !important;
        background:
          radial-gradient(circle at 80% 0%,rgba(244,197,66,.08),transparent 28%),
          #0d0e11 !important;
        color:#fff !important;
        box-shadow:0 -20px 60px rgba(0,0,0,.55) !important;
      }
      .sheet h3{color:#fff !important}
      .close{
        border:1px solid rgba(244,197,66,.22) !important;
        background:#141519 !important;
        color:#f4c542 !important;
      }
      .producthero,
      .thumb{
        background:
          radial-gradient(circle,rgba(244,197,66,.16),transparent 58%),
          #141519 !important;
        border:1px solid rgba(244,197,66,.15) !important;
      }

      .productGallery{
        margin-bottom:14px;
      }
      .producthero{
        position:relative !important;
        overflow:hidden !important;
      }
      .productHeroPhoto{
        width:100% !important;
        height:100% !important;
        min-height:320px;
        object-fit:contain !important;
        display:block;
      }
      .galleryArrow{
        position:absolute;
        top:50%;
        transform:translateY(-50%);
        z-index:4;
        width:42px;
        height:42px;
        border-radius:50%;
        border:1px solid rgba(244,197,66,.45);
        background:rgba(5,5,5,.76);
        color:#f4c542;
        font-size:26px;
        line-height:1;
        display:grid;
        place-items:center;
        backdrop-filter:blur(8px);
        box-shadow:0 8px 22px rgba(0,0,0,.28);
      }
      .galleryArrow.prev{left:10px}
      .galleryArrow.next{right:10px}
      .galleryCounter{
        position:absolute;
        right:12px;
        bottom:10px;
        z-index:4;
        padding:5px 9px;
        border-radius:999px;
        border:1px solid rgba(244,197,66,.35);
        background:rgba(5,5,5,.72);
        color:#f4c542;
        font-size:11px;
        font-weight:900;
        backdrop-filter:blur(8px);
      }
      .productThumbs{
        display:flex;
        gap:8px;
        overflow-x:auto;
        padding:9px 2px 2px;
        scrollbar-width:none;
      }
      .productThumbs::-webkit-scrollbar{display:none}
      .productThumbButton{
        flex:0 0 68px;
        width:68px;
        height:68px;
        padding:0;
        border-radius:13px;
        overflow:hidden;
        border:1px solid rgba(244,197,66,.18);
        background:#111318;
        opacity:.72;
      }
      .productThumbButton.on{
        opacity:1;
        border-color:#f4c542;
        box-shadow:0 0 0 2px rgba(244,197,66,.08),0 0 16px rgba(244,197,66,.18);
      }
      .productThumbButton img{
        width:100%;
        height:100%;
        object-fit:cover;
        display:block;
      }
      @media (max-width:420px){
        .productHeroPhoto{min-height:280px}
        .galleryArrow{width:38px;height:38px;font-size:23px}
        .productThumbButton{flex-basis:62px;width:62px;height:62px}
      }
      .label{
        color:#c7c9cf !important;
        font-weight:800 !important;
      }
      .variant{
        border:1px solid rgba(244,197,66,.18) !important;
        background:#141519 !important;
        color:#b7bac2 !important;
      }
      .variant.on{
        border-color:#f4c542 !important;
        background:rgba(244,197,66,.12) !important;
        color:#f4c542 !important;
      }
      .btn.primary{
        border:0 !important;
        background:linear-gradient(135deg,#f7d45f,#c99414) !important;
        color:#08090b !important;
        font-weight:950 !important;
        box-shadow:0 10px 24px rgba(244,197,66,.18) !important;
      }
      .remove{
        color:#d5a927 !important;
      }

      @media (max-width:420px){
        .card-img{min-height:165px !important;font-size:60px !important}
        .card-body{padding:12px !important}
        .card-title{font-size:13px !important}
        .chip{min-height:40px !important;padding:0 16px !important}
      }

      .sfBannerWrap{
        width:100%;
        margin:14px auto 12px;
        display:flex;
        justify-content:center;
      }
      .sfBannerButton{
        display:block;
        width:100%;
        max-width:680px;
        padding:0;
        border:0;
        background:transparent;
        border-radius:24px;
        overflow:hidden;
        cursor:pointer;
        box-shadow:0 18px 50px rgba(0,0,0,.28);
        -webkit-tap-highlight-color:transparent;
      }
      .sfBannerButton:active{transform:scale(.992)}
      .sfBannerImage{
        display:block;
        width:100%;
        height:auto;
        margin:0 auto;
        object-fit:contain;
        object-position:center center;
        background:#050505;
      }
      .sfTrustGrid{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:7px;
        width:100%;
        margin:0 auto 14px;
      }
      .sfTrustCard{
        min-width:0;
        padding:10px 3px;
        border-radius:14px;
        background:#111318;
        border:1px solid rgba(244,197,66,.18);
        background:linear-gradient(180deg,#15161a,#101115);
        text-align:center;
      }
      .sfTrustCard span{
        display:block;
        margin-bottom:4px;
        font-size:19px;
      }
      .sfTrustCard strong{
        display:block;
        color:#fff;
        font-size:9px;
        line-height:1.2;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }
      .sfTrustCard small{
        display:block;
        margin-top:3px;
        color:#8f949e;
        font-size:8px;
        line-height:1.1;
      }
      @media (min-width:700px){
        .sfBannerButton{max-width:620px}
        .sfTrustGrid{max-width:620px}
      }
      @media (max-width:420px){
        .brandLogo{width:48px;height:48px;flex-basis:48px}
        .sfBannerWrap{margin-top:10px}
        .sfBannerButton{border-radius:20px}
        .sfTrustCard{padding:9px 2px}
        .sfTrustCard span{font-size:18px}
        .sfTrustCard strong{font-size:8.5px}
        .sfTrustCard small{font-size:7.5px}
      }
    `}</style>
    <header className="top">
      <div className="brand">
        <img src="/logo.png" alt="Soccer Fans" className="brandLogo"/>
        <div>
          <b>SOCCER FANS</b>
          <small>{user?.first_name?`Bonjour ${user.first_name}`:"Telegram Store"}</small>
        </div>
      </div>
      <button
        className="cartTopButton"
        onClick={()=>setCartOpen(true)}
        aria-label={`Ouvrir le panier${cart.length ? `, ${cart.length} article${cart.length>1?"s":""}` : ""}`}
      >
        <span className="cartTopIcon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M3.5 4H5l1.65 9.1a2 2 0 0 0 1.97 1.65h7.98a2 2 0 0 0 1.94-1.52L20 7H6.05"
              stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9 19.2h.01M17 19.2h.01"
              stroke="currentColor" strokeWidth="2.8" strokeLinecap="round"/>
          </svg>
        </span>
        {cart.length>0 && <span className="cartTopBadge">{cart.length}</span>}
      </button>
    </header>

    {screen==="shop"&&<Shop/>}
    {screen==="fav"&&<Favorites/>}
    {screen==="account"&&<Account/>}

    <nav className="bottom">
      <button className={"nav "+(screen==="shop"?"on":"")} onClick={()=>setScreen("shop")}><b>⌂</b>Boutique</button>
      <button className={"nav "+(screen==="fav"?"on":"")} onClick={()=>setScreen("fav")}><b>♡</b>Favoris</button>
      <button className="nav" onClick={()=>setCartOpen(true)}><b>🛒</b>Panier</button>
      <button className={"nav "+(screen==="account"?"on":"")} onClick={()=>setScreen("account")}><b>◉</b>Compte</button>
    </nav>

    {selected&&<div className="sheetback" onClick={()=>setSelected(null)}>
      <div className="sheet" onClick={e=>e.stopPropagation()}>
        <button className="close" onClick={()=>setSelected(null)}>✕</button>
        <div className="productGallery">
          <div className="producthero">
            {activeGalleryImage
              ? <img src={activeGalleryImage} alt={`${selected.name} - photo ${galleryIndex+1}`} className="productHeroPhoto"/>
              : <span>{selected.emoji}</span>
            }
            {selectedGallery.length>1&&<>
              <button
                type="button"
                className="galleryArrow prev"
                aria-label="Photo précédente"
                onClick={()=>setGalleryIndex(i=>(i-1+selectedGallery.length)%selectedGallery.length)}
              >‹</button>
              <button
                type="button"
                className="galleryArrow next"
                aria-label="Photo suivante"
                onClick={()=>setGalleryIndex(i=>(i+1)%selectedGallery.length)}
              >›</button>
              <span className="galleryCounter">{galleryIndex+1}/{selectedGallery.length}</span>
            </>}
          </div>

          {selectedGallery.length>1&&
            <div className="productThumbs" aria-label="Photos du produit">
              {selectedGallery.map((img,i)=>
                <button
                  type="button"
                  key={`${img}-${i}`}
                  className={"productThumbButton "+(galleryIndex===i?"on":"")}
                  onClick={()=>setGalleryIndex(i)}
                  aria-label={`Voir la photo ${i+1}`}
                >
                  <img src={img} alt={`${selected.name} miniature ${i+1}`}/>
                </button>
              )}
            </div>
          }
        </div>
        <div className="kicker">{selected.cat}</div>
        <h3>{selected.name}</h3>
        <p className="muted">Choisis ta version, ta taille et ton flocage.</p>

        <div className="label">Version</div>
        <div className="variants">{Object.entries(selected.versions||{Fan:35}).map(([v,p])=><button key={v} className={"variant "+(version===v?"on":"")} onClick={()=>setVersion(v)}>{v} • {fmt(p)}</button>)}</div>

        <div className="label">Taille</div>
        <div className="variants">{["S","M","L","XL","XXL"].map(s=><button key={s} className={"variant "+(size===s?"on":"")} onClick={()=>setSize(s)}>{s}</button>)}</div>

        <div className="label">Flocage personnalisé (+3 €)</div>
        <input className="input" value={printing} onChange={e=>setPrinting(e.target.value)} placeholder="Ex : MBAPPÉ 10"/>

        <div className="sticky-actions"><button className="btn primary" style={{width:"100%"}} onClick={add}>Ajouter • {fmt((selected.versions?.[version]||29)+(printing.trim()?3:0))}</button></div>
      </div>
    </div>}

    {cartOpen&&<div className="sheetback" onClick={()=>setCartOpen(false)}>
      <div className="sheet" onClick={e=>e.stopPropagation()}>
        <button className="close" onClick={()=>setCartOpen(false)}>✕</button>
        <div className="kicker">Commande</div><h3>Ton panier</h3>
        {!cart.length?<div className="empty">Ton panier est vide.</div>:cart.map((x,i)=><div className="cartrow" key={x.key}>
          <div className="thumb">{x.image?<img src={x.image} alt={x.name}/>:x.emoji}</div>
          <div><b>{x.name}</b><div className="tiny">{x.version} • {x.size} • Flocage : {x.printing}</div></div>
          <div style={{textAlign:"right"}}><b>{fmt(x.price)}</b><br/><button className="remove" onClick={()=>setCart(c=>c.filter((_,n)=>n!==i))}>Supprimer</button></div>
        </div>)}

        {!!cart.length&&<>
          <div className="label">Code promo</div>
          <input className="input" value={promo} onChange={e=>setPromo(e.target.value)} placeholder="WELCOME10"/>
          <div className="summary">
            <div className="sumline"><span>Sous-total</span><b>{fmt(subtotal)}</b></div>
            {discount>0&&<div className="sumline"><span>Réduction</span><b>-{fmt(discount)}</b></div>}
            <div className="sumline"><span>Livraison</span><b>{shipping?fmt(shipping):"Offerte"}</b></div>
            <div className="sumline total"><span>Total</span><b>{fmt(total)}</b></div>
          </div>
          <button className="btn primary" style={{width:"100%",marginTop:14}} onClick={checkout}>Commander • {fmt(total)}</button>
        </>}
      </div>
    </div>}
  </main>
}
