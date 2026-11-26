package space.pocketmate.estates;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import net.minecraft.SharedConstants;
import net.minecraft.Bootstrap;
import java.nio.file.*;
import java.util.*;
import com.google.gson.JsonParser;
import static org.junit.jupiter.api.Assertions.*;
class ShopAdminTest {
 @BeforeAll static void boot(){SharedConstants.createGameVersion();Bootstrap.initialize();}
 @TempDir Path root;
 Path file(){return root.resolve("shop.json");}
 ShopAdminStore fresh() throws Exception{return new ShopAdminStore(file());}
 ShopAdminStore.Rule rule(){return new ShopAdminStore.Rule("minecraft:raw_iron","minerals",true,true,200,70);}
 @Test void nonOpCannotReadOrMutateEvenWithValidData() throws Exception{
  var s=fresh();String before=Files.readString(file());assertThrows(SecurityException.class,()->s.view(0));assertThrows(SecurityException.class,()->s.upsert(1,0,rule(),"forged"));assertThrows(SecurityException.class,()->s.disable(0,0,"minecraft:raw_iron","buy","forged"));assertThrows(SecurityException.class,()->s.configure(0,0,ShopPrices.defaults(),true,true,true,true,"x","forged"));assertEquals(before,Files.readString(file()));assertEquals(0,s.revision());
 }
 @Test void flatPriceConfigMigratesOnFirstEditAndKeepsBackup() throws Exception{
  String old=new com.google.gson.Gson().toJson(ShopPrices.defaults());Files.writeString(file(),old);var s=fresh();assertEquals(0,s.revision());assertEquals(old,Files.readString(file()));s.upsert(2,0,rule(),"Admin");assertEquals(old,Files.readString(file().resolveSibling("shop.json.bak")));assertEquals(200,new ShopAdminStore(file()).prices().buy("minecraft:raw_iron",0));assertEquals("Admin",s.view(2).audit().getFirst().actor());
 }
 @Test void deletedDefaultItemStaysAbsentUntilExplicitlyRegisteredAgain() throws Exception {
  var store=fresh();String id="minecraft:raw_iron";
  store.disable(2,0,id,"both","Admin");
  assertTrue(store.entries().containsKey(id));
  assertThrows(SecurityException.class,()->store.delete(0,1,id,"Player"));
  assertThrows(IllegalArgumentException.class,()->store.delete(2,0,id,"Stale admin"));
  store.delete(2,1,id,"Admin");
  var reopened=new ShopAdminStore(file());
  assertFalse(reopened.entries().containsKey(id));
  reopened.upsert(2,2,rule(),"Admin");
  assertTrue(new ShopAdminStore(file()).entries().get(id).sell());
 }
 @Test void blockingRegistrationDeletesTheItemAndRequiresExplicitReRegistration() throws Exception {
  var store=fresh();String id=rule().id();
  store.upsert(2,0,rule(),"Admin");
  assertThrows(SecurityException.class,()->store.setRegistrationAllowed(0,1,id,false,"Player"));
  assertThrows(IllegalArgumentException.class,()->store.setRegistrationAllowed(2,0,id,false,"Stale admin"));
  store.setRegistrationAllowed(2,1,id,false,"Admin");
  var reopened=new ShopAdminStore(file());
  assertFalse(reopened.registrationAllowed(id));
  assertFalse(reopened.entries().containsKey(id));
  assertFalse(reopened.view(2).overrides().containsKey(id));
  assertThrows(IllegalArgumentException.class,()->reopened.upsert(2,2,rule(),"Admin"));
  reopened.setRegistrationAllowed(2,2,id,true,"Admin");
  assertTrue(reopened.registrationAllowed(id));
  assertFalse(reopened.entries().containsKey(id));
  reopened.upsert(2,3,rule(),"Admin");
  assertTrue(new ShopAdminStore(file()).entries().containsKey(id));
 }
 @Test void bulkRegistrationChangesAllMatchesInOneRevisionAndKeepsOperatorRestrictions() throws Exception {
  var store=fresh();
  assertThrows(IllegalArgumentException.class,()->store.setRegistrationAllowedForSearch(2,0," ",false,"Admin"));
  int count=store.setRegistrationAllowedForSearch(2,0,"minecraft:",false,"Admin");
  assertTrue(count>24);
  var reopened=new ShopAdminStore(file());
  assertEquals(1,reopened.revision());
  assertFalse(reopened.entries().containsKey("minecraft:raw_iron"));
  assertFalse(reopened.registrationAllowed("minecraft:raw_iron"));
  assertEquals(count,reopened.setRegistrationAllowedForSearch(2,1,"minecraft:",true,"Admin"));
  assertTrue(reopened.registrationAllowed("minecraft:raw_iron"));
  assertFalse(reopened.entries().containsKey("minecraft:raw_iron"));
  assertFalse(reopened.registrationAllowed("minecraft:command_block"));
 }
 @Test void syncBlocksUnlistedAndFullyPausedItemsButKeepsEitherTradingSide() throws Exception {
  var store=fresh();
  store.disable(2,0,"minecraft:raw_iron","both","Admin");
  store.disable(2,1,"minecraft:raw_copper","buy","Admin");
  assertThrows(SecurityException.class,()->store.syncRegistrationWithShop(0,2,"Player"));
  assertThrows(IllegalArgumentException.class,()->store.syncRegistrationWithShop(2,1,"Stale"));
  assertTrue(store.syncRegistrationWithShop(2,2,"Admin")>0);
  var saved=new ShopAdminStore(file());
  assertEquals(3,saved.revision());
  assertFalse(saved.registrationAllowed("minecraft:stick"));
  assertFalse(saved.registrationAllowed("minecraft:raw_iron"));
  assertFalse(saved.entries().containsKey("minecraft:raw_iron"));
  assertTrue(saved.registrationAllowed("minecraft:raw_copper"));
  assertTrue(saved.entries().get("minecraft:raw_copper").sell());
  assertTrue(saved.registrationAllowed("minecraft:stone"));
  assertEquals(0,saved.syncRegistrationWithShop(2,3,"Admin"));
  assertEquals(3,saved.revision());
 }
 @Test void gimmickProductsUseTwoNativeEntitlementsAndCannotBeSold() {
  assertSame(ShopGimmickUnlock.MEGA,ShopGimmickUnlock.forItem("pixelmon:z_ring"));
  assertSame(ShopGimmickUnlock.MEGA,ShopGimmickUnlock.forItem("pixelmon:key_stone"));
  assertSame(ShopGimmickUnlock.TERA,ShopGimmickUnlock.forItem("pocketmate:tera_orb"));
  assertFalse(ShopAdminStore.saleEditable("pixelmon:z_ring"));
  assertFalse(ShopAdminStore.saleEditable("pixelmon:key_stone"));
  assertFalse(ShopAdminStore.saleEditable("pocketmate:tera_orb"));
  assertTrue(ShopAdminStore.saleEditable("minecraft:stone"));
 }
 @Test void typeSortKeepsExistingEntriesPricesAndTradingFlags() throws Exception {
  var store=fresh();
  store.delete(2,0,"minecraft:raw_iron","Admin");
  var custom=new ShopAdminStore.Rule("minecraft:stone","building",false,true,160,65);
  store.upsert(2,1,custom,"Admin");
  var before=store.entries();
  store.sortExistingByCategory();
  var saved=new ShopAdminStore(file());
  assertEquals(before,saved.entries());
  assertEquals(custom,saved.rule(custom.id()));
  assertFalse(saved.entries().containsKey("minecraft:raw_iron"));
  assertEquals("building",saved.entries().get("minecraft:stone").saleCategory());
  assertEquals(before.values().stream().sorted(ShopCatalog.categoryOrder()).map(ShopCatalog.Entry::id).toList(),
      new ArrayList<>(saved.entries().keySet()));
 }
 @Test void listChangesAndPriceEditsInvalidateOutstandingQuotes() throws Exception{
  var s=fresh();String version=s.version(0);s.upsert(2,0,rule(),"Admin");assertNotEquals(version,s.version(0));assertEquals(70,s.prices().sell("minecraft:raw_iron",0));assertEquals("decoration",new ShopCatalog.Entry("minecraft:raw_iron","decoration",true,true).saleCategory());s.disable(2,1,"minecraft:raw_iron","sell","Admin");assertTrue(s.entries().get("minecraft:raw_iron").buy());assertFalse(s.entries().get("minecraft:raw_iron").sell());s.disable(2,2,"minecraft:raw_iron","both","Admin");assertFalse(s.entries().get("minecraft:raw_iron").buy());s.upsert(2,3,rule(),"Admin");assertTrue(new ShopAdminStore(file()).entries().get("minecraft:raw_iron").sell());
 }
 @Test void addOrdinaryItemsManuallyAndKeepOperatorBlocksAndInvalidSalesRestricted(){
  assertDoesNotThrow(()->new ShopAdminStore.Rule("minecraft:stick","held",true,false,100,50));
  assertDoesNotThrow(()->new ShopAdminStore.Rule("minecraft:stone","building",true,true,100,50));for(String id:List.of("melon","iron_block","diamond_ore","pumpkin","hay_block","glowstone"))assertDoesNotThrow(()->new ShopAdminStore.Rule("minecraft:"+id,"building",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:command_block","building",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:iron_ingot","minerals",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:unknown_item","building",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:raw_iron","minerals",true,true,50,50));
 }
 @Test void staleRevisionDoesNotOverwriteAnotherAdministrator() throws Exception{
  var s=fresh();s.upsert(2,0,rule(),"A");String before=Files.readString(file());assertThrows(IllegalArgumentException.class,()->s.disable(2,0,"minecraft:raw_iron","buy","B"));assertEquals(before,Files.readString(file()));assertEquals(1,s.view(2).audit().size());
 }
 @Test void maintenanceAndRandomPolicyPersistWithIndependentControls() throws Exception{
  var s=fresh();var policy=new ShopPrices(150,60,true,1800,20,123);s.configure(2,0,policy,true,false,true,true,"운영 점검","Admin");var reload=new ShopAdminStore(file());assertTrue(reload.paused(true));assertFalse(reload.paused(false));assertTrue(reload.estatePaused());assertTrue(reload.missionsPaused());assertEquals("운영 점검",reload.reason());assertTrue(reload.prices().randomEnabled());assertEquals(1800,reload.prices().intervalSeconds());
 }
 @Test void saveFailureDoesNotChangeLiveStateAndBadConfigIsNotReset() throws Exception{
  var s=fresh();Files.delete(file());Files.createDirectory(file());Files.writeString(file().resolve("block"),"keep");assertThrows(java.io.IOException.class,()->s.upsert(2,0,rule(),"Admin"));assertEquals(0,s.revision());assertEquals(100,s.prices().buy("minecraft:raw_iron",0));
  Path bad=root.resolve("bad.json");Files.writeString(bad,"{broken}");assertThrows(java.io.IOException.class,()->new ShopAdminStore(bad));assertEquals("{broken}",Files.readString(bad));
 }
 @Test void auditLogIsBoundedAndAllSuccessfulChangesHaveActor() throws Exception{
  var s=fresh();for(int i=0;i<105;i++)s.upsert(2,i,rule(),"Admin");assertEquals(105,s.revision());assertEquals(100,s.view(2).audit().size());assertTrue(s.view(2).audit().stream().allMatch(a->a.actor().equals("Admin")));assertEquals(100,new ShopAdminStore(file()).view(2).audit().size());
 }
 @Test void movesPersistAndCustomerBuySellFiltersUseTheSameOrder() throws Exception{
  var s=fresh();s.move(2,0,"minecraft:raw_iron","minecraft:raw_copper","before","Admin");
  var reload=new ShopAdminStore(file());assertEquals(new ArrayList<>(s.entries().keySet()),new ArrayList<>(reload.entries().keySet()));
  for(boolean buy:List.of(true,false)){
   var ids=reload.entries().values().stream().filter(e->buy?e.buy():e.sell()).map(ShopCatalog.Entry::id).toList();
   assertTrue(ids.indexOf("minecraft:raw_iron")<ids.indexOf("minecraft:raw_copper"));
  }
  assertEquals("품목 순서 변경",reload.view(2).audit().getFirst().action());
 }
 @Test void oldSchemaWithoutOrderMigratesWithoutLosingRules() throws Exception{
  var s=fresh();s.upsert(2,0,rule(),"Admin");var json=JsonParser.parseString(Files.readString(file())).getAsJsonObject();json.remove("order");Files.writeString(file(),json.toString());
  var reload=new ShopAdminStore(file());assertEquals(200,reload.rule("minecraft:raw_iron").buyPrice());assertEquals(List.of(),reload.view(2).order());
  reload.move(2,1,"minecraft:raw_iron","minecraft:raw_copper","before","Admin");assertEquals(200,new ShopAdminStore(file()).rule("minecraft:raw_iron").buyPrice());
 }
 @Test void reorderingRejectsNonOpStaleAndUnknownAnchorsWithoutWriting() throws Exception{
  var s=fresh();String before=Files.readString(file());
  assertThrows(SecurityException.class,()->s.move(0,0,"minecraft:raw_iron","minecraft:raw_copper","before","Fake"));
  assertThrows(IllegalArgumentException.class,()->s.move(2,7,"minecraft:raw_iron","minecraft:raw_copper","before","Stale"));
  assertThrows(IllegalArgumentException.class,()->s.move(2,0,"minecraft:raw_iron","minecraft:not_registered","before","Admin"));
  assertThrows(IllegalArgumentException.class,()->s.move(2,0,"minecraft:raw_iron","minecraft:raw_iron","before","Admin"));
  assertThrows(IllegalArgumentException.class,()->s.move(2,0,"minecraft:raw_iron","minecraft:raw_copper","invalid","Admin"));
  assertEquals(before,Files.readString(file()));assertEquals(0,s.revision());
 }
 @Test void orderSurvivesEditsPausesDeletionAndReRegistration() throws Exception{
  var s=fresh();s.move(2,0,"minecraft:raw_iron","minecraft:raw_copper","before","Admin");var expected=s.view(2).order();
  s.upsert(2,1,rule(),"Admin");s.disable(2,2,"minecraft:raw_iron","both","Admin");s.delete(2,3,"minecraft:raw_iron","Admin");assertFalse(s.entries().containsKey("minecraft:raw_iron"));
  s.upsert(2,4,rule(),"Admin");assertEquals(expected,new ShopAdminStore(file()).view(2).order());
  var ids=new ArrayList<>(s.entries().keySet());assertTrue(ids.indexOf("minecraft:raw_iron")<ids.indexOf("minecraft:raw_copper"));
 }
 @Test void failedOrderSaveRetainsThePreviousLiveOrder() throws Exception{
  var s=fresh();var before=new ArrayList<>(s.entries().keySet());Files.delete(file());Files.createDirectory(file());Files.writeString(file().resolve("block"),"keep");
  assertThrows(java.io.IOException.class,()->s.move(2,0,"minecraft:raw_iron","minecraft:raw_copper","before","Admin"));
  assertEquals(before,new ArrayList<>(s.entries().keySet()));assertEquals(0,s.revision());
 }
}
