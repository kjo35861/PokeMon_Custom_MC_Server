package space.pocketmate.estates;
import com.google.gson.*;
import net.fabricmc.api.ModInitializer;
import net.minecraft.registry.Registries;
import net.minecraft.item.Items;
import net.minecraft.server.network.ServerPlayerEntity;
import java.util.*;

/** Capabilities are derived from the authenticated player, never browser fields. */
public final class AdminMod implements ModInitializer {
 private static final Gson JSON=new Gson();private static final String CHANNEL="pocketmate:admin";
 @Override public void onInitialize(){WebGuiBridge.listen(CHANNEL,(player,payload)->{if(player.getServer()!=null)player.getServer().execute(()->receive(player,payload));});}
 private static String text(JsonObject q,String key,String fallback,int max){if(!q.has(key))return fallback;JsonElement v=q.get(key);if(!v.isJsonPrimitive()||!v.getAsJsonPrimitive().isString())throw new IllegalArgumentException("입력값을 확인해주세요.");String s=v.getAsString();if(s.length()>max)throw new IllegalArgumentException("입력 내용이 너무 깁니다.");return s;}
 private static long number(JsonObject q,String key){try{return q.get(key).getAsBigDecimal().toBigIntegerExact().longValueExact();}catch(Exception e){throw new IllegalArgumentException("정수 값을 입력해주세요.");}}
 private static boolean bool(JsonObject q,String key){JsonElement v=q.get(key);if(v==null||!v.isJsonPrimitive()||!v.getAsJsonPrimitive().isBoolean())throw new IllegalArgumentException("설정 값을 확인해주세요.");return v.getAsBoolean();}
 private static void receive(ServerPlayerEntity player,String payload){
  String request="";
  try{
   if(payload==null||payload.length()>8192)throw new IllegalArgumentException("요청이 너무 큽니다.");JsonObject q=JsonParser.parseString(payload).getAsJsonObject();request=text(q,"requestId","",64);if(!request.matches("[A-Za-z0-9_-]{1,64}"))throw new IllegalArgumentException();String action=text(q,"action","",32);
   int level=player.hasPermissionLevel(2)?2:0;
   if(action.equals("capabilities")){JsonObject out=new JsonObject();out.addProperty("type","capabilities");out.addProperty("canAdmin",level>=2);out.addProperty("requestId",request);WebGuiBridge.emit(player,CHANNEL,out.toString());return;}
   ShopAdminStore.require(level);ShopAdminStore store=ShopMod.adminStore();String actor=NicknamesMod.name(player)+" ("+player.getUuid()+")";String message="";
   switch(action){
    case "view" -> {}
    case "lookup" -> {String query=text(q,"query","",80).toLowerCase(Locale.ROOT).strip();JsonArray items=new JsonArray();if(!query.isEmpty())for(var item:Registries.ITEM){var id=Registries.ITEM.getId(item);String name=ShopCatalog.name(item);if(item==Items.AIR||!id.toString().contains(query)&&!name.toLowerCase(Locale.ROOT).contains(query))continue;JsonObject row=new JsonObject();row.addProperty("id",id.toString());row.addProperty("name",name);row.addProperty("buyAllowed",!ShopCatalog.forbiddenBuy(id.toString()));var base=ShopCatalog.entries().get(id.toString());row.addProperty("sellAllowed",base!=null&&base.sell());if(base!=null)row.addProperty("category",base.category());items.add(row);if(items.size()>=24)break;}JsonObject out=new JsonObject();out.addProperty("type","lookup");out.addProperty("requestId",request);out.add("items",items);WebGuiBridge.emit(player,CHANNEL,out.toString());return;}
    case "upsert" -> {var rule=new ShopAdminStore.Rule(text(q,"item","",160),text(q,"itemCategory","",24),bool(q,"buy"),bool(q,"sell"),number(q,"buyPrice"),number(q,"sellPrice"));store.upsert(level,number(q,"revision"),rule,actor);message="품목 설정을 저장했습니다. 새 거래부터 적용됩니다.";}
    case "disable" -> {store.disable(level,number(q,"revision"),text(q,"item","",160),text(q,"side","",8),actor);message="선택한 거래를 일시정지했습니다.";}
    case "delete" -> {store.delete(level,number(q,"revision"),text(q,"item","",160),actor);message="상점 목록에서 품목을 삭제했습니다.";}
    case "title_save" -> {
     ProfilesMod.adminTitles(player.getServer()).editTitle(text(q,"id","",32),text(q,"name","",40),text(q,"color","",7),text(q,"icon","",8),bool(q,"create"));
     message="칭호를 저장했습니다.";
    }
    case "title_delete" -> {
     ProfilesMod.adminTitles(player.getServer()).deleteTitle(text(q,"id","",32));
     message="칭호와 보유 목록의 해당 칭호를 삭제했습니다.";
    }
    case "configure" -> {var old=store.view(level).prices();var prices=new ShopPrices(number(q,"buyBase"),number(q,"sellBase"),bool(q,"randomEnabled"),number(q,"intervalSeconds"),Math.toIntExact(number(q,"deviationPercent")),old.seed(),old.buyPrices(),old.sellPrices());store.configure(level,number(q,"revision"),prices,bool(q,"buyPaused"),bool(q,"sellPaused"),bool(q,"estatePurchasesPaused"),bool(q,"missionRewardsPaused"),text(q,"maintenanceReason","",120),actor);message="가격·점검 설정을 저장했습니다. 재시작 없이 적용됩니다.";}
    default -> throw new IllegalArgumentException("지원하지 않는 관리자 요청입니다.");
   }
   JsonObject out=snapshot(player,store,q,level);out.addProperty("type","snapshot");out.addProperty("requestId",request);out.addProperty("message",message);WebGuiBridge.emit(player,CHANNEL,out.toString());
  }catch(Exception e){JsonObject out=new JsonObject();out.addProperty("type","error");out.addProperty("requestId",request);out.addProperty("forbidden",e instanceof SecurityException);out.addProperty("message",e instanceof java.io.IOException?"설정을 저장하지 못했습니다. 변경 전 상태를 유지합니다.":e.getMessage()==null?"관리자 요청을 확인해주세요.":e.getMessage());WebGuiBridge.emit(player,CHANNEL,out.toString());}
 }
 private static JsonObject snapshot(ServerPlayerEntity player,ShopAdminStore store,JsonObject q,int level){
  var state=store.view(level);String query=text(q,"query","",80).toLowerCase(Locale.ROOT),category=text(q,"category","all",24),side=text(q,"sideFilter","all",8);long requested=q.has("page")?number(q,"page"):0;
  if(requested<0||requested>1000||!category.equals("all")&&!ShopCatalog.CATEGORIES.contains(category)||!Set.of("all","buy","sell","disabled").contains(side))throw new IllegalArgumentException("목록 조건을 확인해주세요.");
  var list=store.entries().values().stream().filter(e->category.equals("all")||e.category().equals(category)).filter(e->side.equals("all")||side.equals("buy")&&e.buy()||side.equals("sell")&&e.sell()||side.equals("disabled")&&!e.buy()&&!e.sell()).filter(e->query.isEmpty()||e.id().contains(query)||ShopCatalog.name(Registries.ITEM.get(net.minecraft.util.Identifier.of(e.id()))).toLowerCase(Locale.ROOT).contains(query)).toList();int page=(int)Math.min(requested,Math.max(0,(list.size()-1)/24));JsonArray items=new JsonArray();
  for(var e:list.subList(Math.min(page*24,list.size()),Math.min((page+1)*24,list.size()))){var row=JSON.toJsonTree(store.rule(e.id())).getAsJsonObject();row.addProperty("name",ShopCatalog.name(Registries.ITEM.get(net.minecraft.util.Identifier.of(e.id()))));var base=ShopCatalog.entries().get(e.id());row.addProperty("sellAllowed",base!=null&&base.sell());row.addProperty("buyAllowed",!ShopCatalog.forbiddenBuy(e.id()));items.add(row);}
  JsonObject out=new JsonObject();out.addProperty("canAdmin",true);out.addProperty("revision",state.revision());out.addProperty("page",page);out.addProperty("pages",Math.max(1,(list.size()+23)/24));out.addProperty("total",list.size());out.add("items",items);JsonObject policy=new JsonObject();policy.addProperty("buyBase",state.prices().buyBase());policy.addProperty("sellBase",state.prices().sellBase());policy.addProperty("randomEnabled",state.prices().randomEnabled());policy.addProperty("intervalSeconds",state.prices().intervalSeconds());policy.addProperty("deviationPercent",state.prices().deviationPercent());out.add("settings",policy);out.addProperty("buyPaused",state.buyPaused());out.addProperty("sellPaused",state.sellPaused());out.addProperty("estatePurchasesPaused",state.estatePurchasesPaused());out.addProperty("missionRewardsPaused",state.missionRewardsPaused());out.addProperty("maintenanceReason",state.maintenanceReason());out.add("audit",JSON.toJsonTree(state.audit().subList(Math.max(0,state.audit().size()-30),state.audit().size())));
  try{
   var titles=ProfilesMod.adminTitles(player.getServer()).catalog().stream().filter(c->c.kind().equals("title")&&!c.id().equals("none")).toList();
   out.add("titles",JSON.toJsonTree(titles));
  }catch(IllegalStateException unavailable){out.add("titles",JsonNull.INSTANCE);}
  JsonObject status=new JsonObject();status.addProperty("modVersion","0.13.0");status.addProperty("memberLimit",EstateRules.memberLimit(0));status.addProperty("maxEstateLevel",EstateRules.MAX_LEVEL);status.addProperty("maxChunks",EstateRules.limit(10));status.addProperty("missionResetAt",MissionStore.nextReset(java.time.Instant.now()));status.addProperty("pokemonReady",MissionsMod.pokemonReady());
  try{int[] counts=EstatesMod.shopWallet(player.getServer()).adminCounts();status.addProperty("estateReady",true);status.addProperty("estates",counts[0]);status.addProperty("chunks",counts[1]);}catch(Exception unavailable){status.addProperty("estateReady",false);}out.add("status",status);return out;
 }
}
