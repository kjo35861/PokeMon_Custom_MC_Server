package space.pocketmate.estates;

import com.google.gson.*;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.item.*;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.util.Identifier;
import java.nio.file.*;
import java.util.*;

/** Server-thread inventory + shared Pocketmate personal wallet. Client prices are never trusted. */
public final class ShopMod implements ModInitializer {
 private static final String CHANNEL="pocketmate:shop";
 private static final Gson JSON=new Gson();
 private static ShopPrices prices;
 private static ShopAdminStore settings;
 static ShopAdminStore adminStore(){if(settings==null||failure!=null)throw new IllegalStateException(failure==null?"상점을 준비 중입니다.":failure);return settings;}
 static String maintenanceMessage(String message){return settings==null||settings.reason().isBlank()?message:message+" "+settings.reason();}
 static boolean estatePaused(){return settings!=null&&settings.estatePaused();}
 static boolean missionsPaused(){return settings!=null&&settings.missionsPaused();}
 private static String failure;
 private static Path favoritesFile;
 private static final Map<String,LinkedHashSet<String>> favorites=new HashMap<>();
 private static Set<String> favoritesOf(ServerPlayerEntity player){
  return favorites.getOrDefault(player.getUuidAsString(),new LinkedHashSet<>());
 }
 private static void toggleFavorite(ServerPlayerEntity player,String item)throws java.io.IOException{
  if(!settings.entries().containsKey(item))throw new IllegalArgumentException("등록된 상품을 선택해주세요.");
  String id=player.getUuidAsString();
  var next=new LinkedHashSet<>(favoritesOf(player));
  if(!next.remove(item)){
   if(next.size()>=120)throw new IllegalArgumentException("즐겨찾기는 120개까지 등록할 수 있습니다.");
   next.add(item);
  }
  var updated=new HashMap<>(favorites);updated.put(id,next);
  Path temp=Files.createTempFile(favoritesFile.getParent(),"shop-favorites-",".tmp");
  try{
   Files.writeString(temp,JSON.toJson(updated));
   Files.move(temp,favoritesFile,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
   favorites.put(id,next);
  }finally{Files.deleteIfExists(temp);}
 }
 private static final Map<UUID,LinkedHashSet<String>> mutations=new HashMap<>();
 private static final Map<UUID,Long> lastTrade=new HashMap<>();
 @Override public void onInitialize(){
  ServerLifecycleEvents.SERVER_STARTING.register(server->{
   mutations.clear();lastTrade.clear();prices=null;settings=null;failure=null;
   try{
    Path path=FabricLoader.getInstance().getConfigDir().resolve("pocketmate-shop.json");
    favorites.clear();
    favoritesFile=server.getSavePath(net.minecraft.util.WorldSavePath.ROOT).resolve("pocketmate-shop-favorites.json");
    if(Files.exists(favoritesFile)){
     JsonObject saved=JsonParser.parseString(Files.readString(favoritesFile)).getAsJsonObject();
     for(var entry:saved.entrySet()){
      var ids=new LinkedHashSet<String>();
      for(var item:entry.getValue().getAsJsonArray())ids.add(item.getAsString());
      favorites.put(entry.getKey(),ids);
     }
    }
    settings=new ShopAdminStore(path);prices=settings.prices();ShopCatalog.entries();
   }catch(Exception e){failure="상점 설정을 읽지 못했습니다. 거래를 중단했습니다.";org.slf4j.LoggerFactory.getLogger("pocketmate-shop").error("Shop unavailable",e);}
  });
  ServerLifecycleEvents.SERVER_STOPPED.register(server->{mutations.clear();lastTrade.clear();});
  WebGuiBridge.listen(CHANNEL,(player,payload)->{MinecraftServer server=player.getServer();if(server!=null)server.execute(()->receive(player,payload));});
 }
 private static String string(JsonObject o,String key){JsonElement v=o.get(key);if(v==null||!v.isJsonPrimitive()||!v.getAsJsonPrimitive().isString())throw new IllegalArgumentException("올바르지 않은 상점 요청입니다.");return v.getAsString();}
 private static int integer(JsonObject o,String key){try{return o.get(key).getAsBigDecimal().toBigIntegerExact().intValueExact();}catch(Exception e){throw new IllegalArgumentException("올바른 정수 수량을 입력해주세요.");}}
 private static List<ItemStack> slots(ServerPlayerEntity player){List<ItemStack> out=new ArrayList<>();for(int i=0;i<36;i++)out.add(player.getInventory().getStack(i));return out;}
 private static void apply(ServerPlayerEntity player,List<ItemStack> values){for(int i=0;i<36;i++)player.getInventory().setStack(i,values.get(i).copy());player.getInventory().markDirty();player.currentScreenHandler.sendContentUpdates();}
 private static void receive(ServerPlayerEntity player,String payload){
  String requestId="";
  try{
   if(payload==null||payload.length()>16384)throw new IllegalArgumentException("요청이 너무 큽니다.");
   JsonObject q=JsonParser.parseString(payload).getAsJsonObject();requestId=string(q,"requestId");if(!requestId.matches("[A-Za-z0-9_-]{1,64}"))throw new IllegalArgumentException();
   if(failure!=null||prices==null)throw new IllegalStateException(failure==null?"상점을 준비 중입니다.":failure);
   prices=settings.prices();
   ClaimStore wallet=EstatesMod.shopWallet(player.getServer());String action=string(q,"action"),mode=string(q,"mode"),category=string(q,"category");
   if(!Set.of("buy","sell").contains(mode)||(!ShopCatalog.CATEGORIES.contains(category)&&!category.equals("favorites"))||q.has("query")&&string(q,"query").length()>80)throw new IllegalArgumentException("상점 분류를 확인해주세요.");
   int page=q.has("page")?integer(q,"page"):0;if(page<0||page>1000)throw new IllegalArgumentException();
   long now=System.currentTimeMillis();String message="";
   if(action.equals("favorite"))toggleFavorite(player,string(q,"item"));
   if(action.equals("status")){
    JsonObject out=metadata(player,now);out.addProperty("type","status");out.addProperty("requestId",requestId);WebGuiBridge.emit(player,CHANNEL,out.toString());return;
   }
   if(action.equals("quote")){
    boolean buy=mode.equals("buy");var entry=settings.entries().get(string(q,"item"));
    if(entry==null||buy&&!entry.buy()||!buy&&!entry.sell())throw new IllegalArgumentException("해당 거래가 가능한 품목이 아닙니다.");
    if(settings.paused(buy))throw new IllegalArgumentException(maintenanceMessage(buy?"구매가 일시정지되었습니다.":"판매가 일시정지되었습니다."));
    if(player.isSpectator()||player.currentScreenHandler!=player.playerScreenHandler)throw new IllegalArgumentException("보관함을 닫고 일반 플레이 상태에서 거래해주세요.");
    Item item=Registries.ITEM.get(Identifier.of(entry.id()));var inventory=slots(player);long balance=wallet.wallet(player.getUuid()),unit=buy?prices.buy(entry.id(),now):prices.sell(entry.id(),now);
    JsonObject out=metadata(player,now);out.addProperty("type","quote");out.addProperty("requestId",requestId);out.addProperty("item",entry.id());out.addProperty("mode",mode);out.addProperty("unitPrice",unit);out.addProperty("owned",ShopInventory.count(inventory,item));out.addProperty("capacity",ShopInventory.capacity(inventory,item));out.addProperty("maxQuantity",buy?ShopInventory.maxBuy(inventory,item,balance,unit):Math.min(2304,ShopInventory.count(inventory,item)));WebGuiBridge.emit(player,CHANNEL,out.toString());return;
   }
   if(action.equals("trade")||action.equals("bulk")){
    UUID id=player.getUuid();var seen=mutations.computeIfAbsent(id,key->new LinkedHashSet<>());
    if(seen.contains(requestId))throw new IllegalArgumentException("이미 처리한 거래입니다. 목록을 새로고침해주세요.");
    if(now-lastTrade.getOrDefault(id,0L)<250)throw new IllegalArgumentException("잠시 후 거래해주세요.");lastTrade.put(id,now);
    if(!settings.version(now).equals(string(q,"priceVersion")))throw new IllegalArgumentException("가격이 갱신되었습니다. 최신 가격을 확인한 후 다시 거래해주세요.");
    if(player.isSpectator())throw new IllegalArgumentException("관전자 모드에서는 거래할 수 없습니다.");
    if(player.currentScreenHandler!=player.playerScreenHandler)throw new IllegalArgumentException("열려 있는 보관함을 닫은 뒤 거래해주세요.");
    boolean buy=mode.equals("buy");
    if(settings.paused(buy))throw new IllegalArgumentException(settings.reason().isEmpty()?"관리자가 해당 거래를 일시 중지했습니다.":settings.reason());
    List<ItemStack> before=ShopInventory.copy(slots(player)),after=before;
    long total=0;int quantity=0;
    boolean bulk=action.equals("bulk");
    var entries=settings.entries();
    var ids=bulk?favoritesOf(player):Set.of(string(q,"item"));
    if(bulk&&!category.equals("favorites"))throw new IllegalArgumentException("즐겨찾기 탭에서 거래해주세요.");
    var reviewed=new ArrayList<String>();
    for(String itemId:ids){
     var entry=entries.get(itemId);
     if(entry==null||buy&&!entry.buy()||!buy&&!entry.sell()){
      if(bulk)continue;
      throw new IllegalArgumentException("해당 거래가 가능한 품목이 아닙니다.");
     }
     Item item=Registries.ITEM.get(Identifier.of(itemId));
     int amount=bulk?(buy?1:Math.min(2304,ShopInventory.count(after,item))):integer(q,"quantity");
     if(amount==0)continue;
     reviewed.add(itemId+"="+amount);
     after=ShopInventory.plan(after,item,amount,buy);
     total=Math.addExact(total,Math.multiplyExact(buy?prices.buy(itemId,now):prices.sell(itemId,now),amount));
     quantity+=amount;
    }
    if(quantity==0)throw new IllegalArgumentException("거래할 즐겨찾기 상품이 없습니다.");
    Collections.sort(reviewed);
    if(bulk&&!String.join(",",reviewed).equals(string(q,"reviewed")))throw new IllegalArgumentException("거래 수량이 바뀌었습니다. 목록을 새로고침해주세요.");
    long delta=buy?-total:total;
    List<ItemStack> planned=after;
    // Mutate only after a complete plan; roll back memory if wallet persistence rejects/fails.
    ShopTransaction.commit(()->apply(player,planned),()->apply(player,before),()->wallet.shopAdjust(id,delta));
    seen.add(requestId);while(seen.size()>2048)seen.remove(seen.iterator().next());
    ((space.pocketmate.estates.mixin.ShopPlayerSaveInvoker)player.getServer().getPlayerManager()).pocketmate$saveShopPlayer(player);
    message=quantity+"개 "+(buy?"구매":"판매")+"를 완료했습니다. "+String.format("%,d",total)+"원";
   }else if(!action.equals("view")&&!action.equals("favorite"))throw new IllegalArgumentException("올바르지 않은 상점 요청입니다.");
   JsonObject out=snapshot(player,q,mode,category,page,now);out.addProperty("type","snapshot");out.addProperty("requestId",requestId);out.addProperty("message",message);WebGuiBridge.emit(player,CHANNEL,out.toString());
  }catch(Exception e){JsonObject out=new JsonObject();out.addProperty("type","error");out.addProperty("requestId",requestId);out.addProperty("message",e instanceof java.io.IOException?"저장하지 못했습니다. 거래를 적용하지 않았습니다.":e.getMessage()==null?"상점 요청을 확인해주세요.":e.getMessage());WebGuiBridge.emit(player,CHANNEL,out.toString());}
 }
 private static JsonObject snapshot(ServerPlayerEntity player,JsonObject q,String mode,String category,int requestedPage,long now){
  String query=q.has("query")?string(q,"query").trim().toLowerCase(Locale.ROOT):"";
  boolean buy=mode.equals("buy");
  var list=settings.entries().values().stream().filter(e->buy?e.buy():e.sell()).filter(e->category.equals("favorites")?favoritesOf(player).contains(e.id()):(buy?e.category():e.saleCategory()).equals(category)).filter(e->query.isEmpty()||e.id().contains(query)||ShopCatalog.name(Registries.ITEM.get(Identifier.of(e.id()))).toLowerCase(Locale.ROOT).contains(query)).toList();
  int page=Math.min(requestedPage,Math.max(0,(list.size()-1)/24));JsonArray rows=new JsonArray();
  for(var entry:list.subList(Math.min(page*24,list.size()),Math.min((page+1)*24,list.size()))){
   Item item=Registries.ITEM.get(Identifier.of(entry.id()));JsonObject row=new JsonObject();row.addProperty("id",entry.id());row.addProperty("name",ShopCatalog.name(item));row.addProperty("buy",entry.buy()?prices.buy(entry.id(),now):0);row.addProperty("sell",entry.sell()?prices.sell(entry.id(),now):0);row.addProperty("owned",ShopInventory.count(slots(player),item));row.addProperty("maxBuy",ShopInventory.maxBuy(slots(player),item,EstatesMod.shopWallet(player.getServer()).wallet(player.getUuid()),prices.buy(entry.id(),now)));rows.add(row);
  }
  JsonObject out=metadata(player,now);out.addProperty("mode",mode);out.addProperty("category",category);out.addProperty("page",page);out.addProperty("total",list.size());out.addProperty("pages",Math.max(1,(list.size()+23)/24));out.add("items",rows);return out;
 }
 private static JsonObject metadata(ServerPlayerEntity player,long now){
  JsonObject out=new JsonObject();out.add("favorites",JSON.toJsonTree(favoritesOf(player)));out.addProperty("balance",EstatesMod.shopWallet(player.getServer()).wallet(player.getUuid()));out.addProperty("priceVersion",settings.version(now));out.addProperty("nextPriceAt",prices.nextAt(now));out.addProperty("randomPrices",prices.randomEnabled());out.addProperty("buyPaused",settings.paused(true));out.addProperty("sellPaused",settings.paused(false));out.addProperty("maintenanceReason",settings.reason());return out;
 }
}
