package space.pocketmate.estates;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import net.minecraft.SharedConstants;
import net.minecraft.Bootstrap;
import java.nio.file.*;
import java.util.*;
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
 @Test void listChangesAndPriceEditsInvalidateOutstandingQuotes() throws Exception{
  var s=fresh();String version=s.version(0);s.upsert(2,0,rule(),"Admin");assertNotEquals(version,s.version(0));assertEquals(70,s.prices().sell("minecraft:raw_iron",0));assertEquals("minerals",new ShopCatalog.Entry("minecraft:raw_iron","decoration",true,true).saleCategory());s.disable(2,1,"minecraft:raw_iron","sell","Admin");assertTrue(s.entries().get("minecraft:raw_iron").buy());assertFalse(s.entries().get("minecraft:raw_iron").sell());s.disable(2,2,"minecraft:raw_iron","both","Admin");assertFalse(s.entries().get("minecraft:raw_iron").buy());s.upsert(2,3,rule(),"Admin");assertTrue(new ShopAdminStore(file()).entries().get("minecraft:raw_iron").sell());
 }
 @Test void addNewRegisteredBuyItemAndRejectUnsafeSaleCompressionAndProcessedMineral(){
  assertDoesNotThrow(()->new ShopAdminStore.Rule("minecraft:stick","held",true,false,100,50));
  assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:stone","building",true,true,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:iron_block","building",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:iron_ingot","minerals",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:unknown_item","building",true,false,100,50));assertThrows(IllegalArgumentException.class,()->new ShopAdminStore.Rule("minecraft:raw_iron","minerals",true,true,50,50));
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
}
