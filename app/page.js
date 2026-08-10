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
  if(/\bshorts?\b/i.test(low)) return "Short";
  if(/\b(kid|kids|child|children|youth|junior|enfant)\b/i.test(low)) return "Enfant";
  if(/\b(retro|rétro|vintage|classic)\b/i.test(low)) return "Rétro";
  if(/\bplayer\b/i.test(low)) return "Player";
  if(/\bfan\b/i.test(low)) return "Fan";
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
  const [nationRotation,setNationRotation]=useState(0);
  const [leagueRotation,setLeagueRotation]=useState(0);
  const [clubRotation,setClubRotation]=useState(0);

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

  // Rotation automatique des maillots dans les univers
  useEffect(()=>{
    const id=setInterval(()=>setNationRotation(v=>v+1),3500);
    return ()=>clearInterval(id);
  },[]);

  useEffect(()=>{
    const id=setInterval(()=>setLeagueRotation(v=>v+1),4300);
    return ()=>clearInterval(id);
  },[]);

  useEffect(()=>{
    const id=setInterval(()=>setClubRotation(v=>v+1),3900);
    return ()=>clearInterval(id);
  },[]);

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


  function productImagesByTerms(terms=[], preferredCat=""){
    const wanted=(terms||[]).map(t=>String(t).toLowerCase()).filter(Boolean);
    const seen=new Set();

    return products
      .filter(p=>{
        const hay=`${p.name||""} ${p.team||""} ${p.cat||""}`.toLowerCase();
        const catOk=!preferredCat || (p.cat||"").toLowerCase()===preferredCat.toLowerCase();
        return catOk && wanted.some(t=>hay.includes(t)) && p.image;
      })
      .map(p=>p.image)
      .filter(img=>{
        if(!img || seen.has(img)) return false;
        seen.add(img);
        return true;
      });
  }

  function leagueProductImages(leagueName){
    const terms=LEAGUES[leagueName]||[];
    const seen=new Set();

    return products
      .filter(p=>{
        if(!p.image) return false;
        const hay=`${p.name||""} ${p.team||""} ${p.cat||""}`.toLowerCase();
        return terms.some(t=>hay.includes(t));
      })
      .map(p=>p.image)
      .filter(img=>{
        if(!img || seen.has(img)) return false;
        seen.add(img);
        return true;
      });
  }

  function rotatingImage(images,index){
    if(!images?.length) return "";
    return images[index % images.length];
  }

  const nationShowcase = useMemo(()=>{
    const map=new Map();

    products.forEach((p)=>{
      if((p.cat||"").toLowerCase()!=="nations") return;

      const label=String(p.team||"").trim() || String(p.name||"").trim();
      if(!label) return;

      const key=label.toLowerCase();

      if(!map.has(key)){
        map.set(key,{
          code:label.slice(0,2).toUpperCase(),
          label:label.toUpperCase(),
          query:label.toLowerCase(),
          fallback:p.emoji||"🌍",
          images:[]
        });
      }

      const item=map.get(key);

      if(p.image && !item.images.includes(p.image)){
        item.images.push(p.image);
      }

      if(Array.isArray(p.images)){
        p.images.forEach(img=>{
          if(img && !item.images.includes(img)){
            item.images.push(img);
          }
        });
      }

      if((!item.fallback || item.fallback==="🌍") && p.emoji){
        item.fallback=p.emoji;
      }
    });

    return [...map.values()]
      .sort((a,b)=>a.label.localeCompare(b.label,"fr"))
      .map((item,i)=>({
        ...item,
        image:rotatingImage(item.images,nationRotation+i)
      }));
  },[products,nationRotation]);

  const leagueShowcase = useMemo(()=>{
    return Object.keys(LEAGUES)
      .map((league,i)=>{
        const images=leagueProductImages(league);
        return {
          mark:league==="Ligue 1" ? "L1"
            : league==="Premier League" ? "PL"
            : league==="La Liga" ? "LIGA"
            : league==="Serie A" ? "A"
            : league==="Bundesliga" ? "BL"
            : league.slice(0,3).toUpperCase(),
          label:league.toUpperCase(),
          meta:images.length ? `${images.length} maillot(s)` : "Disponible",
          league,
          images,
          image:rotatingImage(images,leagueRotation+i)
        };
      })
      .filter(item=>item.images.length);
  },[products,leagueRotation]);

  const clubShowcase = useMemo(()=>{
    const map=new Map();

    products.forEach((p)=>{
      if((p.cat||"").toLowerCase()!=="clubs") return;

      const label=String(p.team||"").trim();
      if(!label) return;

      const key=label.toLowerCase();

      if(!map.has(key)){
        map.set(key,{
          code:label
            .split(/\s+/)
            .filter(Boolean)
            .slice(0,2)
            .map(x=>x[0])
            .join("")
            .toUpperCase() || label.slice(0,2).toUpperCase(),
          label:label.toUpperCase(),
          query:label.toLowerCase(),
          fallback:p.emoji||"⚽",
          images:[]
        });
      }

      const item=map.get(key);

      if(p.image && !item.images.includes(p.image)){
        item.images.push(p.image);
      }

      if(Array.isArray(p.images)){
        p.images.forEach(img=>{
          if(img && !item.images.includes(img)){
            item.images.push(img);
          }
        });
      }
    });

    return [...map.values()]
      .sort((a,b)=>a.label.localeCompare(b.label,"fr"))
      .map((item,i)=>({
        ...item,
        image:rotatingImage(item.images,clubRotation+i)
      }));
  },[products,clubRotation]);

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

      <section className="sfExactUniverse" aria-label="Nations et championnats">
        <div className="sfExactHeading">
          <span className="sfExactLine"></span>
          <h2><span>🌍</span> NATIONS <em>2026</em></h2>
          <span className="sfExactLine"></span>
        </div>

        <div className="sfExactNations">
          {nationShowcase.map((item)=>(
            <button
              key={item.code}
              className="sfExactNation"
              onClick={()=>jumpToProducts("Nations",item.query,"")}
            >
              <div className="sfExactNationVisual">
                {item.image
                  ? <img key={item.image} src={item.image} alt={item.label} className="sfRotateJersey"/>
                  : <div className="sfExactFallback">{item.fallback}</div>
                }
              </div>
              <div className="sfExactNationName">
                <span>{item.fallback}</span>
                <b>{item.label}</b>
              </div>
            </button>
          ))}
        </div>

        <div className="sfExactHeading sfExactClubHeading">
          <span className="sfExactLine"></span>
          <h2><span>🏆</span> CLUBS & <em>CHAMPIONNATS</em></h2>
          <span className="sfExactLine"></span>
        </div>

        {!!leagueShowcase.length && <>
          <div className="sfExactSubTitle">CHAMPIONNATS</div>
          <div className="sfExactLeagues">
            {leagueShowcase.map((item)=>(
              <button
                key={item.label}
                className={"sfExactLeague "+(activeLeague===item.league?"on":"")}
                onClick={()=>jumpToProducts("Clubs","",item.league)}
              >
                <div className="sfExactLeagueVisual">
                  {item.image
                    ? <img key={item.image} src={item.image} alt={item.label} className="sfRotateJersey"/>
                    : <div className="sfExactLeagueMark">{item.mark}</div>
                  }
                </div>
                <strong>{item.label}</strong>
                <small>{item.meta}</small>
              </button>
            ))}
          </div>
        </>}

        {!!clubShowcase.length && <>
          <div className="sfExactSubTitle sfExactClubSubTitle">TOUS LES CLUBS</div>
          <div className="sfExactClubs">
            {clubShowcase.map((item)=>(
              <button
                key={item.label}
                className="sfExactClub"
                onClick={()=>jumpToProducts("Clubs",item.query,"")}
              >
                <div className="sfExactClubVisual">
                  {item.image
                    ? <img key={item.image} src={item.image} alt={item.label} className="sfRotateJersey"/>
                    : <div className="sfExactClubFallback">{item.fallback}</div>
                  }
                </div>
                <div className="sfExactClubName">
                  <strong>{item.code}</strong>
                  <span>{item.label}</span>
                </div>
              </button>
            ))}
          </div>
        </>}

        <div className="sfExactMotto">
          <span></span>
          <b>QUALITÉ</b><i>•</i><b>PASSION</b><i>•</i><b>PERFORMANCE</b>
          <span></span>
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

      /* =========================================================
         SOCCER FANS — STYLE RÉFÉRENCE NOIR / OR
         Surcharge finale : garde toutes les fonctions existantes
         ========================================================= */

      :root{
        --sf-gold:#f4c542;
        --sf-gold-2:#d79d16;
        --sf-gold-soft:#ffd965;
        --sf-black:#050607;
        --sf-panel:#0c0d10;
        --sf-panel-2:#111216;
        --sf-line:rgba(244,197,66,.42);
        --sf-muted:#8c8f97;
      }

      html,body{
        background:#050607 !important;
      }

      body{
        color:#fff !important;
      }

      /* En-tête */
      .top{
        position:relative !important;
        z-index:10 !important;
        padding:14px 4px 10px !important;
        background:
          radial-gradient(circle at 12% 0%,rgba(244,197,66,.08),transparent 28%),
          #050607 !important;
      }

      .brandLogo{
        width:54px !important;
        height:54px !important;
        flex-basis:54px !important;
        border:1px solid rgba(244,197,66,.48) !important;
        box-shadow:0 0 22px rgba(244,197,66,.16) !important;
      }

      .brand b{
        font-size:16px !important;
        letter-spacing:.01em !important;
        font-weight:950 !important;
      }

      .brand small{
        margin-top:3px !important;
        color:#b4b5ba !important;
      }

      .cartTopButton{
        width:56px !important;
        height:56px !important;
        border-radius:18px !important;
        border:1px solid rgba(244,197,66,.48) !important;
        background:
          radial-gradient(circle at 50% 35%,rgba(244,197,66,.10),transparent 55%),
          #0c0d10 !important;
        color:var(--sf-gold) !important;
        box-shadow:0 0 22px rgba(244,197,66,.09) !important;
      }

      /* Livraison */
      .promoRow{
        min-height:54px !important;
        margin:10px 0 14px !important;
        padding:0 15px !important;
        border-radius:15px !important;
        border:1px solid rgba(244,197,66,.43) !important;
        background:#090a0c !important;
        color:#e4b73c !important;
        font-size:14px !important;
        justify-content:center !important;
        box-shadow:
          inset 0 0 0 1px rgba(255,255,255,.015),
          0 0 22px rgba(244,197,66,.06) !important;
      }

      /* Recherche */
      .searchBarWrap{
        margin-bottom:13px !important;
      }

      .searchBar{
        min-height:58px !important;
        border-radius:16px !important;
        border:1px solid rgba(244,197,66,.34) !important;
        background:#0b0c0f !important;
        padding:0 13px 0 16px !important;
        gap:12px !important;
      }

      .searchIcon{
        color:#c4c6cd !important;
        font-size:27px !important;
      }

      .searchBar input{
        font-size:14px !important;
        color:#fff !important;
      }

      .searchBar input::placeholder{
        color:#666a73 !important;
      }

      .filterBtn{
        width:42px !important;
        height:42px !important;
        border:0 !important;
        background:transparent !important;
        color:var(--sf-gold) !important;
        font-size:21px !important;
      }

      /* Catégories */
      .chipsPremium{
        gap:9px !important;
        margin-bottom:20px !important;
        padding:1px 0 6px !important;
      }

      .chipsPremium .chip{
        min-height:44px !important;
        padding:0 21px !important;
        border-radius:14px !important;
        border:1px solid rgba(244,197,66,.28) !important;
        background:#0a0b0d !important;
        color:#c8c9ce !important;
        font-size:13px !important;
        font-weight:850 !important;
      }

      .chipsPremium .chip.on{
        color:#fff2c2 !important;
        border-color:#ffd458 !important;
        background:
          radial-gradient(circle at 50% 30%,rgba(244,197,66,.20),transparent 65%),
          #151109 !important;
        box-shadow:
          0 0 0 1px rgba(255,211,88,.12),
          0 0 19px rgba(244,197,66,.24),
          inset 0 0 15px rgba(244,197,66,.08) !important;
      }

      /* Bloc catalogue */
      .sectionPremium{
        padding-top:10px !important;
      }

      .premiumHead{
        margin-bottom:17px !important;
        align-items:flex-end !important;
      }

      .premiumHead .kicker{
        color:#d7a72e !important;
        font-size:10px !important;
        letter-spacing:.18em !important;
      }

      .premiumHead h2{
        margin:5px 0 0 !important;
        font-size:29px !important;
        line-height:1 !important;
        letter-spacing:-.035em !important;
        font-weight:950 !important;
      }

      .premiumHead h2::after{
        width:58px !important;
        height:3px !important;
        margin-top:10px !important;
        background:linear-gradient(90deg,#ffd45a,#c68b00) !important;
        box-shadow:0 0 10px rgba(244,197,66,.30) !important;
      }

      .premiumHead > span{
        padding-bottom:4px !important;
        color:#d7a72e !important;
        font-size:13px !important;
        font-weight:850 !important;
      }

      /* 2 cartes par ligne comme la référence */
      .premiumGrid{
        display:grid !important;
        grid-template-columns:repeat(2,minmax(0,1fr)) !important;
        gap:11px !important;
      }

      .premiumCard{
        min-width:0 !important;
        overflow:hidden !important;
        border-radius:17px !important;
        border:1px solid rgba(244,197,66,.52) !important;
        background:#090a0c !important;
        box-shadow:
          0 0 0 1px rgba(244,197,66,.04) inset,
          0 0 18px rgba(244,197,66,.08),
          0 13px 25px rgba(0,0,0,.30) !important;
      }

      /* Zone photo : cadrage plus proche de la référence */
      .premiumVisual{
        position:relative !important;
        isolation:isolate !important;
        min-height:0 !important;
        height:auto !important;
        aspect-ratio:1 / 1.12 !important;
        padding:0 !important;
        display:block !important;
        overflow:hidden !important;
        background:
          radial-gradient(circle at 50% 80%,rgba(244,197,66,.10),transparent 48%),
          radial-gradient(circle at 50% 10%,rgba(244,197,66,.07),transparent 35%),
          #0b0c0e !important;
        border-bottom:1px solid rgba(244,197,66,.22) !important;
      }

      .premiumVisual::before{
        content:"" !important;
        position:absolute !important;
        inset:0 !important;
        z-index:3 !important;
        pointer-events:none !important;
        background:
          linear-gradient(180deg,rgba(0,0,0,.00) 50%,rgba(0,0,0,.18) 100%),
          radial-gradient(circle at 50% 50%,transparent 50%,rgba(0,0,0,.25) 100%) !important;
      }

      .premiumVisual::after{
        content:"" !important;
        position:absolute !important;
        inset:0 !important;
        z-index:1 !important;
        opacity:.55 !important;
        pointer-events:none !important;
        background:
          linear-gradient(125deg,transparent 40%,rgba(244,197,66,.08) 40.5%,transparent 41%),
          linear-gradient(35deg,transparent 58%,rgba(244,197,66,.05) 58.5%,transparent 59%) !important;
      }

      .productGlow{
        width:150px !important;
        height:150px !important;
        left:50% !important;
        bottom:3% !important;
        transform:translateX(-50%) !important;
        opacity:.55 !important;
        z-index:0 !important;
      }

      /* Important : centre parfaitement les vraies photos Yupoo */
      .premiumVisual .productPhoto{
        position:absolute !important;
        inset:0 !important;
        z-index:2 !important;
        width:100% !important;
        height:100% !important;
        max-width:none !important;
        object-fit:cover !important;
        object-position:center center !important;
        transform:scale(1.015) !important;
        filter:
          contrast(1.02)
          saturate(.95)
          brightness(.96)
          drop-shadow(0 12px 20px rgba(0,0,0,.30)) !important;
      }

      /* Le petit filigrane d'équipe reste discret derrière l'image */
      .productMark{
        left:10px !important;
        bottom:8px !important;
        z-index:1 !important;
        font-size:52px !important;
        color:rgba(244,197,66,.055) !important;
      }

      /* Badges */
      .premiumBadge{
        top:9px !important;
        left:9px !important;
        z-index:6 !important;
        padding:5px 9px !important;
        border-radius:5px !important;
        color:#08090b !important;
        background:linear-gradient(135deg,#ffd964,#d99d15) !important;
        font-size:9px !important;
        font-weight:950 !important;
        box-shadow:0 4px 12px rgba(0,0,0,.24) !important;
      }

      .premiumHeart{
        top:6px !important;
        right:6px !important;
        z-index:6 !important;
        width:38px !important;
        height:38px !important;
        padding:0 !important;
        border:0 !important;
        background:rgba(0,0,0,.15) !important;
        color:#fff !important;
        font-size:25px !important;
        text-shadow:0 2px 7px rgba(0,0,0,.8) !important;
        backdrop-filter:none !important;
      }

      /* Texte carte */
      .premiumCardBody{
        min-height:108px !important;
        padding:10px 11px 11px !important;
        background:
          linear-gradient(180deg,#0b0c0e,#08090a) !important;
        border-top:0 !important;
      }

      .premiumCard .card-title{
        min-height:34px !important;
        margin:0 !important;
        color:#fff !important;
        font-size:12.5px !important;
        line-height:1.22 !important;
        font-weight:900 !important;
        display:-webkit-box !important;
        -webkit-line-clamp:2 !important;
        -webkit-box-orient:vertical !important;
        overflow:hidden !important;
      }

      .premiumCard .meta{
        margin-top:4px !important;
        color:#8f9299 !important;
        font-size:10px !important;
        line-height:1.2 !important;
        white-space:nowrap !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
      }

      .premiumCard .price{
        margin-top:6px !important;
        color:#eab72d !important;
        font-size:16px !important;
        line-height:1 !important;
        font-weight:950 !important;
        letter-spacing:.01em !important;
      }

      /* CTA bas */
      .collectionCta{
        min-height:59px !important;
        margin-top:16px !important;
        border-radius:15px !important;
        border:1px solid rgba(244,197,66,.60) !important;
        background:#090a0b !important;
        color:#d8a62c !important;
        font-size:14px !important;
        box-shadow:0 0 18px rgba(244,197,66,.06) !important;
      }

      .collectionCtaIcon{
        font-size:20px !important;
      }

      .collectionCtaArrow{
        font-size:25px !important;
      }

      /* Barre de navigation basse */
      .bottom{
        border-top:1px solid rgba(244,197,66,.16) !important;
        background:rgba(7,8,10,.97) !important;
        backdrop-filter:blur(18px) !important;
        box-shadow:0 -12px 30px rgba(0,0,0,.34) !important;
      }

      .nav{
        color:#797c84 !important;
        font-size:10px !important;
      }

      .nav b{
        margin-bottom:4px !important;
        font-size:22px !important;
      }

      .nav.on{
        color:var(--sf-gold) !important;
      }

      /* Galerie fiche produit : garde les vraies images complètes */
      .producthero{
        border-radius:18px !important;
        background:#0b0c0e !important;
      }

      .productHeroPhoto{
        object-fit:contain !important;
        object-position:center center !important;
        background:#0b0c0e !important;
      }

      .productThumbButton{
        border-radius:10px !important;
        background:#0c0d10 !important;
      }

      .productThumbButton img{
        object-fit:cover !important;
        object-position:center center !important;
      }

      /* Mobile */
      @media (max-width:420px){
        .promoRow{
          font-size:12px !important;
          gap:6px !important;
          padding:0 10px !important;
        }

        .chipsPremium .chip{
          min-height:41px !important;
          padding:0 17px !important;
          font-size:12px !important;
        }

        .premiumHead h2{
          font-size:27px !important;
        }

        .premiumGrid{
          gap:9px !important;
        }

        .premiumCard{
          border-radius:15px !important;
        }

        .premiumCardBody{
          min-height:101px !important;
          padding:9px 10px 10px !important;
        }

        .premiumCard .card-title{
          font-size:11.5px !important;
          min-height:29px !important;
        }

        .premiumCard .price{
          font-size:15px !important;
        }
      }

      /* Tablette / PC : on élargit sans perdre l'esprit de la référence */
      @media (min-width:760px){
        .premiumGrid{
          grid-template-columns:repeat(3,minmax(0,1fr)) !important;
          gap:14px !important;
        }

        .premiumCard .card-title{
          font-size:14px !important;
        }

        .premiumCard .price{
          font-size:18px !important;
        }
      }

      @media (min-width:1100px){
        .premiumGrid{
          grid-template-columns:repeat(4,minmax(0,1fr)) !important;
        }
      }



      /* ===== BLOC COLLECTIONS — STYLE CARTES COMME TA CAPTURE ===== */
      .sfShowcase{
        margin:12px 0 24px;
        padding:16px 12px 14px;
        border-radius:24px;
        border:1px solid rgba(244,197,66,.22);
        background:
          radial-gradient(circle at 50% 0%, rgba(244,197,66,.08), transparent 34%),
          linear-gradient(180deg,#111216,#0a0b0e);
        box-shadow:0 16px 40px rgba(0,0,0,.26);
      }
      .sfShowcaseTop{
        display:flex;
        align-items:flex-end;
        justify-content:space-between;
        gap:12px;
        margin-bottom:14px;
      }
      .sfShowcaseTop h2{
        margin:4px 0 0;
        color:#fff;
        font-size:25px;
        line-height:1.05;
      }
      .sfShowcaseTop > span{
        color:#f4c542;
        font-weight:950;
        font-size:17px;
      }
      .sfShowcasePanel{
        padding:12px;
        border-radius:22px;
        border:1px solid rgba(244,197,66,.18);
        background:linear-gradient(180deg, rgba(20,22,27,.96), rgba(11,12,16,.98));
        box-shadow: inset 0 0 0 1px rgba(255,255,255,.02);
      }
      .sfShowcasePanel + .sfShowcasePanel{ margin-top:12px; }
      .sfShowcasePanelHead{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:12px;
        flex-wrap:wrap;
      }
      .sfShowcaseTitle{
        display:flex;
        align-items:center;
        gap:8px;
        color:#fff;
        font-size:14px;
        letter-spacing:.03em;
      }
      .sfShowcasePill{
        min-height:32px;
        padding:0 14px;
        display:inline-flex;
        align-items:center;
        justify-content:center;
        border-radius:999px;
        border:1px solid rgba(244,197,66,.32);
        background:rgba(244,197,66,.08);
        color:#f4c542;
        font-size:12px;
        font-weight:900;
        white-space:nowrap;
      }
      .sfNationHeroGrid{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:10px;
      }
      .sfNationHeroCard{
        min-width:0;
        padding:10px 8px 12px;
        border-radius:18px;
        border:1px solid rgba(244,197,66,.20);
        background:linear-gradient(180deg,#171a20,#0d0f13);
        box-shadow:0 10px 24px rgba(0,0,0,.18);
        color:#fff;
      }
      .sfNationHeroCard:active{ transform:scale(.98); }
      .sfNationHeroVisual{
        height:130px;
        border-radius:16px;
        background:
          radial-gradient(circle at 50% -10%, rgba(244,197,66,.10), transparent 42%),
          linear-gradient(180deg,#16191f,#0f1116);
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        padding:10px;
      }
      .sfNationHeroPhoto{
        width:100%;
        height:100%;
        object-fit:contain;
        display:block;
        filter: drop-shadow(0 8px 18px rgba(0,0,0,.32));
      }
      .sfNationHeroFallback{
        font-size:58px;
        line-height:1;
      }
      .sfNationHeroText{
        margin-top:10px;
        text-align:center;
      }
      .sfNationHeroText strong{
        display:block;
        color:#fff;
        font-size:15px;
        font-weight:950;
        letter-spacing:.03em;
      }
      .sfNationHeroText span{
        display:block;
        color:rgba(255,255,255,.88);
        font-size:10px;
        margin-top:3px;
        text-transform:uppercase;
        letter-spacing:.04em;
      }
      .sfLeagueHeroGrid{
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:10px;
      }
      .sfLeagueHeroCard{
        min-width:0;
        min-height:106px;
        padding:12px 8px 10px;
        border-radius:18px;
        border:1px solid rgba(244,197,66,.18);
        background:linear-gradient(180deg,#16191f,#0d1015);
        color:#fff;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:flex-start;
        text-align:center;
        gap:6px;
      }
      .sfLeagueHeroCard.on{
        border-color:#f4c542;
        box-shadow:0 0 0 2px rgba(244,197,66,.08),0 0 18px rgba(244,197,66,.14);
      }
      .sfLeagueHeroIcon{
        width:46px;
        height:46px;
        border-radius:14px;
        display:grid;
        place-items:center;
        font-size:14px;
        font-weight:950;
        color:#fff;
        background:linear-gradient(180deg,#2a2f3a,#171b22);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);
      }
      .sfLeagueHeroIcon.l1{ background:linear-gradient(180deg,#383d49,#1e232b); }
      .sfLeagueHeroIcon.pl{ background:linear-gradient(180deg,#43404f,#231f30); }
      .sfLeagueHeroIcon.liga{ background:linear-gradient(180deg,#4d4038,#261f19); }
      .sfLeagueHeroIcon.sa{ background:linear-gradient(180deg,#2d4450,#17222b); }
      .sfLeagueHeroIcon.bl{ background:linear-gradient(180deg,#4d2f2f,#271617); }
      .sfLeagueHeroIcon.ucl{ background:linear-gradient(180deg,#28334a,#121926); }
      .sfLeagueHeroCard strong{
        font-size:11px;
        line-height:1.1;
      }
      .sfLeagueHeroCard small{
        color:rgba(255,255,255,.62);
        font-size:9px;
        line-height:1.2;
      }
      .sfServiceRow{
        margin-top:12px;
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:8px;
      }
      .sfServiceCard{
        min-width:0;
        padding:10px 6px;
        border-radius:16px;
        border:1px solid rgba(244,197,66,.16);
        background:linear-gradient(180deg,#121418,#0c0e12);
        color:#fff;
        text-align:center;
      }
      .sfServiceCard span{
        display:block;
        font-size:18px;
        margin-bottom:6px;
      }
      .sfServiceCard b{
        display:block;
        font-size:10px;
        line-height:1.1;
        letter-spacing:.03em;
      }
      .sfServiceCard small{
        display:block;
        margin-top:3px;
        color:rgba(255,255,255,.66);
        font-size:8px;
      }
      @media (max-width:420px){
        .sfShowcase{ padding:14px 10px 12px; }
        .sfShowcaseTop h2{ font-size:22px; }
        .sfNationHeroGrid{ gap:8px; }
        .sfNationHeroVisual{ height:112px; padding:8px; }
        .sfNationHeroText strong{ font-size:13px; }
        .sfNationHeroText span{ font-size:9px; }
        .sfLeagueHeroGrid{ gap:8px; }
        .sfLeagueHeroCard{ min-height:98px; padding:10px 6px; }
        .sfLeagueHeroIcon{ width:40px; height:40px; font-size:12px; }
        .sfLeagueHeroCard strong{ font-size:10px; }
        .sfLeagueHeroCard small{ font-size:8px; }
        .sfServiceRow{ gap:6px; }
        .sfServiceCard{ padding:9px 4px; }
        .sfServiceCard b{ font-size:9px; }
        .sfServiceCard small{ font-size:7px; }
      }



      /* ===== UNIVERS EXACT — NATIONS 2026 / CLUBS & CHAMPIONNATS ===== */
      .sfExactUniverse{
        margin:12px 0 24px;
        padding:18px 12px 14px;
        border-radius:22px;
        background:
          radial-gradient(circle at 50% 18%,rgba(244,197,66,.06),transparent 30%),
          #050505;
        border:1px solid rgba(244,197,66,.16);
        overflow:hidden;
      }
      .sfExactHeading{
        display:grid;
        grid-template-columns:1fr auto 1fr;
        align-items:center;
        gap:12px;
        margin:0 0 14px;
      }
      .sfExactHeading h2{
        margin:0;
        color:#fff;
        font-size:24px;
        line-height:1;
        font-weight:950;
        letter-spacing:.035em;
        white-space:nowrap;
      }
      .sfExactHeading h2 em{
        color:#e9b434;
        font-style:normal;
      }
      .sfExactLine{
        height:2px;
        background:linear-gradient(90deg,transparent,#e2ad2d 50%,transparent);
        box-shadow:0 0 8px rgba(244,197,66,.18);
      }

      .sfExactNations{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:8px;
      }
      .sfExactNation{
        min-width:0;
        border:0;
        padding:0;
        background:transparent;
        color:#fff;
      }
      .sfExactNationVisual{
        height:170px;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        background:
          radial-gradient(circle at 50% 55%,rgba(244,197,66,.05),transparent 50%),
          #050505;
      }
      .sfRotateJersey{
        width:100%;
        height:100%;
        object-fit:contain;
        object-position:center center;
        display:block;
        animation:sfJerseySwap .48s ease both;
        filter:drop-shadow(0 13px 20px rgba(0,0,0,.52));
      }
      @keyframes sfJerseySwap{
        from{opacity:0;transform:scale(.93) translateY(4px)}
        to{opacity:1;transform:scale(1) translateY(0)}
      }
      .sfExactFallback{
        font-size:62px;
      }
      .sfExactNationName{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:6px;
        margin-top:4px;
        font-size:11px;
      }
      .sfExactNationName span{font-size:19px}
      .sfExactNationName b{
        color:#fff;
        font-size:12px;
        letter-spacing:.02em;
      }

      .sfExactClubHeading{margin-top:17px}

      .sfExactLeagues{
        display:grid;
        grid-template-columns:repeat(5,minmax(0,1fr));
        gap:7px;
      }
      .sfExactLeague{
        min-width:0;
        min-height:154px;
        padding:9px 6px 10px;
        border-radius:15px;
        border:1px solid rgba(238,182,48,.74);
        background:
          radial-gradient(circle at 50% 25%,rgba(244,197,66,.06),transparent 45%),
          linear-gradient(180deg,#0d0d0e,#070708);
        color:#fff;
        text-align:center;
        overflow:hidden;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.015);
      }
      .sfExactLeague.on{
        box-shadow:0 0 0 2px rgba(244,197,66,.11),0 0 16px rgba(244,197,66,.18);
      }
      .sfExactLeagueVisual{
        height:92px;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        margin-bottom:5px;
      }
      .sfExactLeagueMark{
        font-size:24px;
        font-weight:950;
        color:#fff;
      }
      .sfExactLeague strong{
        display:block;
        font-size:10px;
        line-height:1.05;
        color:#fff;
      }
      .sfExactLeague small{
        display:block;
        margin-top:5px;
        color:#e3b438;
        font-size:7.5px;
        line-height:1.1;
      }

      .sfExactMotto{
        margin-top:15px;
        display:flex;
        align-items:center;
        justify-content:center;
        gap:8px;
        color:#fff;
      }
      .sfExactMotto span{
        flex:1;
        max-width:100px;
        height:2px;
        background:linear-gradient(90deg,transparent,#d8a62e);
      }
      .sfExactMotto span:last-child{
        background:linear-gradient(90deg,#d8a62e,transparent);
      }
      .sfExactMotto b{
        font-size:9px;
        letter-spacing:.22em;
        font-weight:500;
      }
      .sfExactMotto i{
        color:#d8a62e;
        font-style:normal;
      }

      @media (max-width:420px){
        .sfExactUniverse{padding:14px 8px 12px}
        .sfExactHeading{gap:7px}
        .sfExactHeading h2{font-size:18px}
        .sfExactNations{gap:4px}
        .sfExactNationVisual{height:126px}
        .sfExactNationName{gap:3px}
        .sfExactNationName span{font-size:15px}
        .sfExactNationName b{font-size:9px}
        .sfExactLeagues{gap:4px}
        .sfExactLeague{
          min-height:126px;
          padding:7px 3px 8px;
          border-radius:12px;
        }
        .sfExactLeagueVisual{height:72px}
        .sfExactLeague strong{font-size:7.5px}
        .sfExactLeague small{font-size:6px}
        .sfExactMotto{gap:5px}
        .sfExactMotto b{font-size:7px;letter-spacing:.14em}
      }



      /* Tous les pays Nations : défilement horizontal */
      .sfExactNations{
        display:grid !important;
        grid-auto-flow:column !important;
        grid-auto-columns:minmax(155px,1fr) !important;
        grid-template-columns:none !important;
        gap:8px !important;
        overflow-x:auto !important;
        overflow-y:hidden !important;
        padding:2px 2px 10px !important;
        scroll-snap-type:x mandatory !important;
        scrollbar-width:none !important;
        -webkit-overflow-scrolling:touch !important;
      }

      .sfExactNations::-webkit-scrollbar{
        display:none !important;
      }

      .sfExactNation{
        scroll-snap-align:start !important;
      }

      @media (max-width:420px){
        .sfExactNations{
          grid-auto-columns:calc((100vw - 54px)/2.25) !important;
          gap:6px !important;
        }
        .sfExactNationVisual{
          height:138px !important;
        }
      }

      @media (min-width:700px){
        .sfExactNations{
          grid-auto-columns:minmax(180px,1fr) !important;
        }
      }



      /* Tous les championnats + tous les clubs */
      .sfExactSubTitle{
        margin:4px 2px 9px;
        color:#e3b438;
        font-size:10px;
        font-weight:950;
        letter-spacing:.15em;
      }

      .sfExactClubSubTitle{
        margin-top:15px;
      }

      .sfExactLeagues{
        display:grid !important;
        grid-auto-flow:column !important;
        grid-auto-columns:minmax(150px,1fr) !important;
        grid-template-columns:none !important;
        gap:7px !important;
        overflow-x:auto !important;
        overflow-y:hidden !important;
        padding:2px 2px 10px !important;
        scroll-snap-type:x mandatory !important;
        scrollbar-width:none !important;
        -webkit-overflow-scrolling:touch !important;
      }

      .sfExactLeagues::-webkit-scrollbar,
      .sfExactClubs::-webkit-scrollbar{
        display:none !important;
      }

      .sfExactLeague{
        scroll-snap-align:start !important;
      }

      .sfExactClubs{
        display:grid;
        grid-auto-flow:column;
        grid-auto-columns:minmax(150px,1fr);
        gap:7px;
        overflow-x:auto;
        overflow-y:hidden;
        padding:2px 2px 10px;
        scroll-snap-type:x mandatory;
        scrollbar-width:none;
        -webkit-overflow-scrolling:touch;
      }

      .sfExactClub{
        min-width:0;
        border:1px solid rgba(238,182,48,.55);
        border-radius:15px;
        padding:8px 6px 10px;
        background:
          radial-gradient(circle at 50% 25%,rgba(244,197,66,.05),transparent 44%),
          linear-gradient(180deg,#0d0d0e,#070708);
        color:#fff;
        scroll-snap-align:start;
        overflow:hidden;
      }

      .sfExactClubVisual{
        height:112px;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
      }

      .sfExactClubFallback{
        font-size:48px;
      }

      .sfExactClubName{
        margin-top:6px;
        text-align:center;
      }

      .sfExactClubName strong{
        display:block;
        color:#e3b438;
        font-size:10px;
        line-height:1;
      }

      .sfExactClubName span{
        display:block;
        margin-top:4px;
        color:#fff;
        font-size:8px;
        line-height:1.1;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }

      @media (max-width:420px){
        .sfExactLeagues,
        .sfExactClubs{
          grid-auto-columns:calc((100vw - 54px)/2.25) !important;
          gap:6px !important;
        }

        .sfExactLeague{
          min-height:132px !important;
        }

        .sfExactClubVisual{
          height:105px;
        }

        .sfExactClubName span{
          font-size:7.5px;
        }
      }

      @media (min-width:700px){
        .sfExactLeagues,
        .sfExactClubs{
          grid-auto-columns:minmax(175px,1fr) !important;
        }
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
