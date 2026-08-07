"use client";

import { useEffect, useMemo, useState } from "react";

const PRODUCTS = [
  {id:1,name:"Real Madrid Domicile 26/27",team:"Real Madrid",cat:"Clubs",versions:{Fan:29,Player:39},emoji:"⚪",hot:true},
  {id:2,name:"Paris Domicile 26/27",team:"Paris",cat:"Clubs",versions:{Fan:29,Player:39},emoji:"🔵",hot:true},
  {id:3,name:"Barcelone Domicile 26/27",team:"Barcelone",cat:"Clubs",versions:{Fan:29,Player:39},emoji:"🔴"},
  {id:4,name:"France Domicile 2026",team:"France",cat:"Nations",versions:{Fan:29,Player:39},emoji:"🇫🇷",hot:true},
  {id:5,name:"Brésil Rétro 2002",team:"Brésil",cat:"Rétro",versions:{Rétro:34},emoji:"🇧🇷"},
  {id:6,name:"Argentine Domicile",team:"Argentine",cat:"Nations",versions:{Fan:29,Player:39},emoji:"🇦🇷"},
  {id:7,name:"Milan Rétro 06/07",team:"Milan",cat:"Rétro",versions:{Rétro:34},emoji:"🔴"},
  {id:8,name:"Kit Enfant France",team:"France",cat:"Enfant",versions:{Enfant:32},emoji:"🧒"}
];

const fmt = n => new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"}).format(n);

export default function Home(){
  const [tg,setTg]=useState(null);
  const [user,setUser]=useState(null);
  const [query,setQuery]=useState("");
  const [cat,setCat]=useState("Tous");
  const [selected,setSelected]=useState(null);
  const [version,setVersion]=useState("");
  const [size,setSize]=useState("M");
  const [printing,setPrinting]=useState("");
  const [cart,setCart]=useState([]);
  const [favs,setFavs]=useState([]);
  const [screen,setScreen]=useState("shop");
  const [cartOpen,setCartOpen]=useState(false);
  const [promo,setPromo]=useState("");

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

  useEffect(()=>{localStorage.setItem("sf_cart_pro",JSON.stringify(cart))},[cart]);
  useEffect(()=>{localStorage.setItem("sf_favs",JSON.stringify(favs))},[favs]);

  const filtered=useMemo(()=>PRODUCTS.filter(p=>{
    const okCat=cat==="Tous"||p.cat===cat;
    const q=query.toLowerCase();
    const okQ=!q||(`${p.name} ${p.team} ${p.cat}`).toLowerCase().includes(q);
    return okCat&&okQ;
  }),[cat,query]);

  const subtotal=cart.reduce((s,x)=>s+x.price*x.qty,0);
  const discount=promo.trim().toUpperCase()==="WELCOME10"?subtotal*.10:0;
  const shipping=subtotal===0?0:(subtotal>=100?0:5.90);
  const total=Math.max(0,subtotal-discount+shipping);

  function openProduct(p){
    setSelected(p);
    setVersion(Object.keys(p.versions)[0]);
    setSize("M"); setPrinting("");
    try{tg?.HapticFeedback?.impactOccurred("light")}catch{}
  }
  function add(){
    const price=selected.versions[version]+(printing.trim()?3:0);
    setCart(c=>[...c,{key:crypto.randomUUID?.()||Date.now(),id:selected.id,name:selected.name,emoji:selected.emoji,version,size,printing:printing.trim()||"Aucun",price,qty:1}]);
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
      <section className="hero">
        <div>
          <div className="kicker">Nouvelle collection</div>
          <h1>Le maillot<br/>qu'il te faut.</h1>
          <p>Fan, Player, rétro et enfants. Personnalise ton maillot directement dans Telegram.</p>
          <button className="btn primary" onClick={()=>document.getElementById("products")?.scrollIntoView()}>Découvrir</button>
        </div>
      </section>
      <div className="notice">🎁 Livraison offerte dès 100 € • Code démo <b>WELCOME10</b> : -10 %</div>
      <div className="search"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Rechercher club, nation, saison…"/></div>
      <div className="chips">
        {["Tous","Clubs","Nations","Rétro","Enfant"].map(x=><button key={x} className={"chip "+(cat===x?"on":"")} onClick={()=>setCat(x)}>{x}</button>)}
      </div>
      <section id="products" className="section">
        <div className="section-head"><div><div className="kicker">Catalogue</div><h2>Maillots populaires</h2></div><span>{filtered.length} produits</span></div>
        <div className="grid">
          {filtered.map(p=><article className="card" key={p.id}>
            {p.hot&&<span className="badge">🔥 TOP</span>}
            <button className="heart" onClick={()=>setFavs(f=>f.includes(p.id)?f.filter(id=>id!==p.id):[...f,p.id])}>{favs.includes(p.id)?"♥":"♡"}</button>
            <div className="card-img" onClick={()=>openProduct(p)}>{p.emoji}</div>
            <div className="card-body" onClick={()=>openProduct(p)}>
              <div className="card-title">{p.name}</div>
              <div className="meta">{Object.keys(p.versions).join(" • ")}</div>
              <div className="price">Dès {fmt(Math.min(...Object.values(p.versions)))}</div>
            </div>
          </article>)}
        </div>
      </section>
    </>
  }

  function Favorites(){
    const items=PRODUCTS.filter(p=>favs.includes(p.id));
    return <section className="section">
      <div className="section-head"><div><div className="kicker">Sélection</div><h2>Mes favoris</h2></div></div>
      {!items.length?<div className="empty">♡ Aucun favori pour le moment.</div>:
      <div className="grid">{items.map(p=><article className="card" key={p.id} onClick={()=>openProduct(p)}><div className="card-img">{p.emoji}</div><div className="card-body"><div className="card-title">{p.name}</div><div className="price">Dès {fmt(Math.min(...Object.values(p.versions)))}</div></div></article>)}</div>}
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

  return <main className="app">
    <header className="top">
      <div className="brand"><div className="logo">SF</div><div><b>SOCCER FANS</b><small>{user?.first_name?`Bonjour ${user.first_name}`:"Telegram Store"}</small></div></div>
      <button className="iconbtn" onClick={()=>setCartOpen(true)}>🛒 {cart.length||""}</button>
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
        <div className="producthero">{selected.emoji}</div>
        <div className="kicker">{selected.cat}</div>
        <h3>{selected.name}</h3>
        <p className="muted">Choisis ta version, ta taille et ton flocage.</p>

        <div className="label">Version</div>
        <div className="variants">{Object.entries(selected.versions).map(([v,p])=><button key={v} className={"variant "+(version===v?"on":"")} onClick={()=>setVersion(v)}>{v} • {fmt(p)}</button>)}</div>

        <div className="label">Taille</div>
        <div className="variants">{["S","M","L","XL","XXL"].map(s=><button key={s} className={"variant "+(size===s?"on":"")} onClick={()=>setSize(s)}>{s}</button>)}</div>

        <div className="label">Flocage personnalisé (+3 €)</div>
        <input className="input" value={printing} onChange={e=>setPrinting(e.target.value)} placeholder="Ex : MBAPPÉ 10"/>

        <div className="sticky-actions"><button className="btn primary" style={{width:"100%"}} onClick={add}>Ajouter • {fmt((selected.versions[version]||0)+(printing.trim()?3:0))}</button></div>
      </div>
    </div>}

    {cartOpen&&<div className="sheetback" onClick={()=>setCartOpen(false)}>
      <div className="sheet" onClick={e=>e.stopPropagation()}>
        <button className="close" onClick={()=>setCartOpen(false)}>✕</button>
        <div className="kicker">Commande</div><h3>Ton panier</h3>
        {!cart.length?<div className="empty">Ton panier est vide.</div>:cart.map((x,i)=><div className="cartrow" key={x.key}>
          <div className="thumb">{x.emoji}</div>
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
