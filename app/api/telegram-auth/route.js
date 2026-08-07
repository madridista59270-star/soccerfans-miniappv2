import crypto from "crypto";
import { NextResponse } from "next/server";

function validateTelegramInitData(initData, botToken, maxAgeSeconds=3600){
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  if(!hash) return {ok:false, reason:"missing_hash"};

  const authDate = Number(params.get("auth_date") || 0);
  if(!authDate || Math.abs(Date.now()/1000-authDate)>maxAgeSeconds) return {ok:false, reason:"expired"};

  params.delete("hash");
  const dataCheckString=[...params.entries()]
    .sort(([a],[b])=>a.localeCompare(b))
    .map(([k,v])=>`${k}=${v}`)
    .join("\n");

  const secretKey=crypto.createHmac("sha256","WebAppData").update(botToken).digest();
  const calculated=crypto.createHmac("sha256",secretKey).update(dataCheckString).digest("hex");

  const valid=calculated.length===hash.length &&
    crypto.timingSafeEqual(Buffer.from(calculated),Buffer.from(hash));
  if(!valid) return {ok:false, reason:"bad_signature"};

  let user=null;
  try{ user=JSON.parse(params.get("user")||"null"); }catch{}
  return {ok:true,user};
}

export async function POST(req){
  const {initData}=await req.json();
  const botToken=process.env.TELEGRAM_BOT_TOKEN;
  if(!botToken) return NextResponse.json({ok:false,error:"Server not configured"},{status:500});
  const result=validateTelegramInitData(initData,botToken);
  return NextResponse.json(result,{status:result.ok?200:401});
}
