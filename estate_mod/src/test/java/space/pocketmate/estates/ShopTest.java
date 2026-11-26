package space.pocketmate.estates;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import net.minecraft.SharedConstants;
import net.minecraft.Bootstrap;
import net.minecraft.item.*;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class ShopTest {
 @BeforeAll static void boot(){SharedConstants.createGameVersion();Bootstrap.initialize();}
 @TempDir Path root;
 @Test void catalogHasAllRequestedGroupsAndNoProcessedMineralsOrCompressionArbitrage() throws Exception{
  var all=ShopCatalog.entries();assertTrue(all.size()>300);
  assertEquals("building",all.get("minecraft:stone").category());assertEquals("colored",all.get("minecraft:red_wool").category());assertEquals("decoration",all.get("minecraft:torch").category());
  for(String id:List.of("raw_iron","raw_gold","raw_copper","diamond","coal","lapis_lazuli","quartz","ancient_debris"))assertTrue(all.get("minecraft:"+id).sell());
  for(String id:List.of("iron_ingot","iron_nugget","gold_ingot","gold_nugget","copper_ingot","netherite_ingot","netherite_scrap","diamond_block","raw_iron_block","iron_block","coal_block","hay_block","melon","glowstone","diamond_ore","stone_stairs","stone_slab","command_block","bedrock"))assertFalse(all.containsKey("minecraft:"+id),id);
  assertTrue(all.get("minecraft:chorus_flower").buy());assertTrue(all.get("minecraft:chorus_fruit").sell());assertTrue(all.get("minecraft:wheat_seeds").buy());assertTrue(all.get("minecraft:wheat_seeds").sell());assertFalse(all.get("minecraft:wheat").buy());assertTrue(all.get("minecraft:wheat").sell());
  assertTrue(all.values().stream().filter(ShopCatalog.Entry::sell).allMatch(e->e.category().equals(e.saleCategory())));
  for(String category:List.of("balls","held","zcrystals","megastones"))assertTrue(all.values().stream().noneMatch(e->e.category().equals(category)));
  assertEquals("decoration",all.get("minecraft:torchflower").category());assertTrue(all.get("minecraft:torchflower").buy());assertEquals("decoration",all.get("minecraft:torchflower").saleCategory());
  assertEquals("돌",ShopCatalog.name(Items.STONE));
  var report=new com.google.gson.JsonObject();var rows=new com.google.gson.JsonArray();
  for(var e:all.values()){var row=new com.google.gson.Gson().toJsonTree(e).getAsJsonObject();row.addProperty("name",ShopCatalog.name(net.minecraft.registry.Registries.ITEM.get(net.minecraft.util.Identifier.of(e.id()))));row.addProperty("buyPrice",e.buy()?100:0);row.addProperty("sellPrice",e.sell()?50:0);rows.add(row);}
  report.addProperty("registry_bootstrap_only",true);report.addProperty("game_tested",false);report.addProperty("count",all.size());report.add("items",rows);
  Path out=Path.of("build/reports/shop-catalog.json");Files.createDirectories(out.getParent());Files.writeString(out,new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(report));

 }
 @Test void fixedAndFutureWindowPricesAreServerStableAndBelowBuy(){
  var fixed=ShopPrices.defaults();assertEquals(100,fixed.buy("x",0));assertEquals(50,fixed.sell("x",99999999));assertEquals(fixed.version(0),fixed.version(Long.MAX_VALUE));assertEquals(0,fixed.nextAt(0));
  var random=new ShopPrices(100,50,true,3600,15,1234);
  for(int i=0;i<100;i++){long price=random.sell("minecraft:"+i,1);assertTrue(price>=42&&price<=58);assertEquals(price,random.sell("minecraft:"+i,3_599_999));}
  assertNotEquals(random.version(0),random.version(3_600_000));assertEquals(3_600_000,random.nextAt(0));assertNotEquals(fixed.version(0),new ShopPrices(101,50,false,3600,15,1234).version(0));
  assertThrows(IllegalArgumentException.class,()->new ShopPrices(50,50,false,3600,15,0));
 }
 @Test void inventoryPlanMergesStacksAndRejectsFullWithoutMutatingOriginal(){
  List<ItemStack> slots=new ArrayList<>();slots.add(new ItemStack(Items.STONE,60));slots.add(ItemStack.EMPTY);
  var after=ShopInventory.plan(slots,Items.STONE,10,true);assertEquals(64,after.get(0).getCount());assertEquals(6,after.get(1).getCount());assertEquals(60,slots.get(0).getCount());
  assertThrows(IllegalArgumentException.class,()->ShopInventory.plan(List.of(new ItemStack(Items.DIRT,64)),Items.STONE,1,true));
  assertThrows(IllegalArgumentException.class,()->ShopInventory.plan(slots,Items.STONE,0,true));assertThrows(IllegalArgumentException.class,()->ShopInventory.plan(slots,Items.STONE,2305,true));
 }
 @Test void componentVariantsArePurchasedAndCountedSeparately(){
  var normal=new ItemStack(Items.STONE,12);
  var variant=new ItemStack(Items.STONE);
  variant.set(net.minecraft.component.DataComponentTypes.CUSTOM_NAME,net.minecraft.text.Text.literal("Variant"));
  var bought=ShopInventory.plan(List.of(normal,ItemStack.EMPTY),variant,3,true);
  assertEquals(12,ShopInventory.count(bought,Items.STONE));
  assertEquals(3,ShopInventory.count(bought,variant));
  assertEquals(1,variant.getCount());
  assertTrue(ItemStack.areItemsAndComponentsEqual(variant,bought.get(1)));
 }
 @Test void salesUseExactPlainComponentsAndQuantity(){
  var named=new ItemStack(Items.DIAMOND,8);named.set(net.minecraft.component.DataComponentTypes.CUSTOM_NAME,net.minecraft.text.Text.literal("Keep me"));
  List<ItemStack> slots=List.of(named,new ItemStack(Items.DIAMOND,3));assertEquals(3,ShopInventory.count(slots,Items.DIAMOND));
  var after=ShopInventory.plan(slots,Items.DIAMOND,2,false);assertEquals(8,after.get(0).getCount());assertEquals(1,after.get(1).getCount());assertEquals(3,slots.get(1).getCount());
  assertThrows(IllegalArgumentException.class,()->ShopInventory.plan(slots,Items.DIAMOND,4,false));
 }
 @Test void walletSharesBalancesPersistsAndRejectsInsufficientFunds() throws Exception{
  Path file=root.resolve("estate.json");var store=new ClaimStore(file);UUID player=UUID.randomUUID();store.creditWallet(player,1000);store.shopAdjust(player,-300);store.shopAdjust(player,50);assertEquals(750,new ClaimStore(file).wallet(player));
  assertThrows(ClaimStore.Denied.class,()->store.shopAdjust(player,-751));assertEquals(750,store.wallet(player));
  String before=Files.readString(file);Files.delete(file);Files.createDirectory(file);assertThrows(java.io.IOException.class,()->store.shopAdjust(player,100));assertEquals(750,store.wallet(player));Files.delete(file);Files.writeString(file,before);
 }
 @Test void walletWriteFailureRestoresInventoryAndSuccessKeepsIt() throws Exception{
  var state=new java.util.concurrent.atomic.AtomicInteger(10);
  assertThrows(java.io.IOException.class,()->ShopTransaction.commit(()->state.set(20),()->state.set(10),()->{throw new java.io.IOException("simulated persistence failure");}));assertEquals(10,state.get());
  ShopTransaction.commit(()->state.set(20),()->state.set(10),()->{});assertEquals(20,state.get());
 }

 @Test void perItemBasesAndJsonConfigurationAreSupported(){
  var values=new ShopPrices(100,50,false,3600,15,10,Map.of("minecraft:diamond",200L),Map.of("minecraft:diamond",75L));assertEquals(200,values.buy("minecraft:diamond",0));assertEquals(75,values.sell("minecraft:diamond",0));assertEquals(50,values.sell("minecraft:coal",0));
  assertEquals(values,new com.google.gson.Gson().fromJson(new com.google.gson.Gson().toJson(values),ShopPrices.class));
  assertThrows(IllegalArgumentException.class,()->new ShopPrices(100,50,false,3600,15,10,Map.of("minecraft:diamond",40L),Map.of()));
 }

 @Test void maxPurchaseAccountsForPartialStacksFundsAndFullInventory(){
  var slots=new ArrayList<ItemStack>(Collections.nCopies(36,new ItemStack(Items.DIRT,64)));
  slots.set(0,new ItemStack(Items.STONE,60));slots.set(1,ItemStack.EMPTY);
  assertEquals(68,ShopInventory.capacity(slots,Items.STONE));assertEquals(68,ShopInventory.maxBuy(slots,Items.STONE,100000,100));assertEquals(25,ShopInventory.maxBuy(slots,Items.STONE,2599,100));assertEquals(0,ShopInventory.maxBuy(slots,Items.STONE,99,100));
  assertEquals(60,slots.get(0).getCount());var filled=ShopInventory.plan(slots,Items.STONE,68,true);assertEquals(64,filled.get(0).getCount());assertEquals(64,filled.get(1).getCount());assertEquals(0,ShopInventory.capacity(filled,Items.STONE));
 }
 @Test void maxDoesNotMergeNamedItemsAndRespectsUnstackableItems(){
  var named=new ItemStack(Items.STONE,10);named.set(net.minecraft.component.DataComponentTypes.CUSTOM_NAME,net.minecraft.text.Text.literal("Protected"));
  assertEquals(64,ShopInventory.capacity(List.of(named,ItemStack.EMPTY),Items.STONE));assertEquals(0,ShopInventory.count(List.of(named),Items.STONE));
  assertEquals(36,ShopInventory.maxBuy(Collections.nCopies(36,ItemStack.EMPTY),Items.DIAMOND_PICKAXE,Long.MAX_VALUE,100));
  assertEquals(2304,ShopInventory.maxBuy(Collections.nCopies(36,ItemStack.EMPTY),Items.STONE,Long.MAX_VALUE,100));
 }
 @Test void sellingAllEligibleStacksLeavesNamedStacksUntouched(){
  var named=new ItemStack(Items.DIAMOND,4);named.set(net.minecraft.component.DataComponentTypes.CUSTOM_NAME,net.minecraft.text.Text.literal("Protected"));
  var slots=List.of(new ItemStack(Items.DIAMOND,64),named,new ItemStack(Items.DIAMOND,17));int max=ShopInventory.count(slots,Items.DIAMOND);assertEquals(81,max);var sold=ShopInventory.plan(slots,Items.DIAMOND,max,false);assertTrue(sold.get(0).isEmpty());assertTrue(sold.get(2).isEmpty());assertEquals(4,sold.get(1).getCount());
 }

}
