const COUNTRIES = [
  "Worldwide",
  "England",
  "France",
  "Spain",
  "Italy",
  "Germany",
  "Portugal",
  "Netherlands",
  "Belgium",
  "Scotland",
  "Turkey",
  "Greece",
  "Austria",
  "Switzerland",
  "Brazil",
  "Argentina",
  "Colombia",
  "Uruguay",
  "Mexico",
  "USA",
  "Japan",
  "Saudi Arabia",
  "Morocco",
  "South Africa",
  "Australia"
];

const API_KEY = "123";

function cleanLeague(row, fallbackCountry=""){
  const id=String(row?.idLeague||"").trim();
  const name=String(row?.strLeague||"").trim();
  const sport=String(row?.strSport||"Soccer").trim().toLowerCase();
  const logo=String(row?.strBadge||row?.strLogo||"").trim();

  if(!id || !name || !logo) return null;
  if(sport && sport!=="soccer" && sport!=="football") return null;

  return {
    id,
    name,
    country:String(row?.strCountry||fallbackCountry||"Football").trim(),
    logo
  };
}

async function fetchCountry(country){
  const url=
    `https://www.thesportsdb.com/api/v1/json/${API_KEY}/search_all_leagues.php`+
    `?c=${encodeURIComponent(country)}&s=Soccer`;

  try{
    const res=await fetch(url,{
      next:{revalidate:86400},
      headers:{"User-Agent":"SoccerFansMiniApp/1.0"}
    });

    if(!res.ok) return [];

    const data=await res.json();
    const rows=Array.isArray(data?.countries)
      ? data.countries
      : Array.isArray(data?.leagues)
        ? data.leagues
        : [];

    return rows
      .map(row=>cleanLeague(row,country))
      .filter(Boolean);
  }catch{
    return [];
  }
}

export async function GET(){
  const results=await Promise.all(COUNTRIES.map(fetchCountry));

  const byId=new Map();

  for(const list of results){
    for(const item of list){
      if(!byId.has(item.id)){
        byId.set(item.id,item);
      }
    }
  }

  const leagueItems=[...byId.values()].sort((a,b)=>{
    const countryCompare=a.country.localeCompare(b.country,"fr");
    if(countryCompare!==0) return countryCompare;
    return a.name.localeCompare(b.name,"fr");
  });

  return Response.json(
    {
      leagueItems,
      count:leagueItems.length,
      countriesChecked:COUNTRIES.length
    },
    {
      headers:{
        "Cache-Control":"public, s-maxage=86400, stale-while-revalidate=604800"
      }
    }
  );
}
