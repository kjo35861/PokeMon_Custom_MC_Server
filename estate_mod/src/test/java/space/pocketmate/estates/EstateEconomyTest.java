package space.pocketmate.estates;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import com.google.gson.*;
import static org.junit.jupiter.api.Assertions.*;

class EstateEconomyTest {
    @TempDir Path root;
    UUID lord=UUID.randomUUID(),member=UUID.randomUUID();
    Path file(){return root.resolve("estate.json");}
    ClaimStore load() throws Exception{return new ClaimStore(file());}
    ClaimStore fresh() throws Exception {var s=load();s.createEstate(lord,"Lord","숲 마을",0,0);return s;}
    List<ClaimStore.Key> line(int from,int to){return java.util.stream.IntStream.rangeClosed(from,to).mapToObj(x->new ClaimStore.Key(x,0)).toList();}
    ClaimStore paid() throws Exception {var s=fresh();s.upgrade(lord,0);s.buyBatch(lord,"Lord",line(1,3));s.creditTreasury(lord,50_000,lord,true);s.upgrade(lord,1);return s;}
    @Test void scheduleMatchesRequestedLevelsAndRisingPrices(){
        assertEquals(1,EstateRules.limit(0));assertEquals(4,EstateRules.limit(1));assertEquals(36,EstateRules.limit(10));assertEquals(0,EstateRules.cost(1));assertEquals(50_000,EstateRules.cost(2));
        assertEquals(0,EstateRules.purchasePrice(1,3));assertEquals(20_000,EstateRules.nextChunkPrice(4));assertEquals(42_500,EstateRules.purchasePrice(4,2));assertEquals(97_500,EstateRules.nextChunkPrice(35));assertEquals(1_880_000,EstateRules.purchasePrice(4,32));assertEquals(20_000,EstateRules.purchasePrice(2,3));
    }
    @Test void creationStartsAtZeroAndFirstUpgradeIsFree() throws Exception {
        var s=fresh();assertEquals(0,s.progress(lord).level());assertEquals(1,s.owned(lord).size());assertEquals(0,s.wallet(lord));
        assertEquals(ClaimStore.Failure.CHUNK_LIMIT,assertThrows(ClaimStore.Rejected.class,()->s.buyBatch(lord,"Lord",line(1,1))).reason);
        s.upgrade(lord,0);s.buyBatch(lord,"Lord",line(1,3));assertEquals(4,s.owned(lord).size());assertEquals(0,s.progress(lord).treasury());
        assertEquals(ClaimStore.Failure.CHUNK_LIMIT,assertThrows(ClaimStore.Rejected.class,()->s.buyBatch(lord,"Lord",line(4,4))).reason);
    }
    @Test void upgradeRequiresLordVaultBalanceAndExpectedLevel() throws Exception {
        var s=fresh();s.upgrade(lord,0);s.creditWallet(lord,50_000);
        assertThrows(ClaimStore.Denied.class,()->s.upgrade(lord,1));assertEquals(50_000,s.wallet(lord));
        s.deposit(lord,50_000);s.upgrade(lord,1);assertEquals(2,s.progress(lord).level());assertEquals(0,s.progress(lord).treasury());
        assertThrows(ClaimStore.Denied.class,()->s.upgrade(lord,1));assertThrows(ClaimStore.Denied.class,()->s.upgrade(member,2));
    }
    @Test void purchaseUsesVaultFirstAndOnlyMissingAmountFromLord() throws Exception {
        var s=paid();s.creditWallet(lord,42_500);s.deposit(lord,10_000);s.buyBatch(lord,"Lord",line(4,5));
        assertEquals(6,s.owned(lord).size());assertEquals(0,s.wallet(lord));assertEquals(0,s.progress(lord).treasury());
        var ledger=s.progress(lord).ledger();assertEquals("AUTO_DEPOSIT",ledger.get(ledger.size()-2).type());assertEquals(32_500,ledger.get(ledger.size()-2).amount());assertEquals(42_500,ledger.getLast().amount());
        assertEquals(s.progress(lord),load().progress(lord));assertEquals(0,load().wallet(lord));
    }
    @Test void enoughVaultNeverTouchesPersonalMoney() throws Exception {
        var s=paid();s.creditTreasury(lord,100_000,lord,true);s.creditWallet(lord,75_000);s.buyBatch(lord,"Lord",line(4,4));
        assertEquals(80_000,s.progress(lord).treasury());assertEquals(75_000,s.wallet(lord));
    }
    @Test void insufficientCombinedBalanceRejectsWholePurchaseWithoutDebit() throws Exception {
        var s=paid();s.creditWallet(lord,42_499);s.deposit(lord,10_000);String before=Files.readString(file());
        assertThrows(ClaimStore.Denied.class,()->s.buyBatch(lord,"Lord",line(4,5)));assertEquals(before,Files.readString(file()));assertEquals(10_000,s.progress(lord).treasury());assertEquals(32_499,s.wallet(lord));assertNull(s.get(4,0));
    }
    @Test void membersMayDepositOwnMoneyButCannotUpgradeOrSpendAsLord() throws Exception {
        var s=fresh();s.seen(member,"Member",1);s.invite(lord,member);s.answerInvite(member,lord,true);s.creditWallet(member,20_000);s.deposit(member,15_000);
        assertEquals(5_000,s.wallet(member));assertEquals(15_000,s.progress(lord).treasury());assertThrows(ClaimStore.Denied.class,()->s.upgrade(member,0));assertThrows(ClaimStore.Rejected.class,()->s.buyBatch(member,"Member",line(1,1)));
    }
    @Test void capAtThirtySixAndMaxLevelRejectWithoutCharge() throws Exception {
        var s=fresh();s.creditTreasury(lord,10_000_000,lord,true);for(int level=0;level<10;level++)s.upgrade(lord,level);
        s.buyBatch(lord,"Lord",line(1,35));assertEquals(36,s.owned(lord).size());String before=Files.readString(file());
        assertThrows(ClaimStore.Denied.class,()->s.upgrade(lord,10));assertEquals(ClaimStore.Failure.CHUNK_LIMIT,assertThrows(ClaimStore.Rejected.class,()->s.buyBatch(lord,"Lord",line(36,36))).reason);assertEquals(before,Files.readString(file()));
    }
    @Test void failedSaveRollsBackWalletVaultLandAndCounter() throws Exception {
        var s=paid();s.creditWallet(lord,50_000);var before=s.progress(lord);Files.move(file(),root.resolve("before.json"));Files.createDirectory(file());Files.writeString(file().resolve("blocker"),"block");
        assertThrows(java.io.IOException.class,()->s.buyBatch(lord,"Lord",line(4,5)));assertEquals(before,s.progress(lord));assertEquals(50_000,s.wallet(lord));assertEquals(4,s.owned(lord).size());
        assertThrows(java.io.IOException.class,()->s.deposit(lord,10_000));assertEquals(50_000,s.wallet(lord));assertEquals(before,s.progress(lord));
    }
    @Test void concurrentPurchasesCannotSpendSameMoneyTwice() throws Exception {
        var s=paid();s.creditWallet(lord,20_000);ExecutorService pool=Executors.newFixedThreadPool(2);CountDownLatch go=new CountDownLatch(1);
        try{List<Future<Boolean>> attempts=new ArrayList<>();for(int z:List.of(-1,1))attempts.add(pool.submit(()->{go.await();try{s.buyBatch(lord,"Lord",List.of(new ClaimStore.Key(0,z)));return true;}catch(ClaimStore.Denied rejected){return false;}}));go.countDown();int wins=0;for(var future:attempts)if(future.get())wins++;assertEquals(1,wins);assertEquals(5,s.owned(lord).size());assertEquals(0,s.wallet(lord));}finally{pool.shutdownNow();}
    }
    @Test void v2MigrationKeepsExistingClaimsAtSmallestAdequateLevel() throws Exception {
        var s=fresh();s.creditTreasury(lord,10_000_000,lord,true);for(int level=0;level<5;level++)s.upgrade(lord,level);s.buyBatch(lord,"Lord",line(1,15));
        JsonObject old=JsonParser.parseString(Files.readString(file())).getAsJsonObject();old.addProperty("formatVersion",2);old.remove("progress");old.remove("balances");Files.writeString(file(),old.toString());
        var migrated=load();assertEquals(16,migrated.owned(lord).size());assertEquals(5,migrated.progress(lord).level());assertEquals(0,migrated.progress(lord).treasury());assertEquals(16,migrated.progress(lord).purchasedChunks());
        migrated.seen(lord,"Lord",1);assertEquals(5,load().progress(lord).level());
    }
    @Test void invalidAmountsAndCorruptProgressCannotMintOrReset() throws Exception {
        var s=fresh();for(long amount:List.of(0L,-1L,Long.MAX_VALUE))assertThrows(ClaimStore.Denied.class,()->s.creditWallet(lord,amount));assertThrows(ClaimStore.Denied.class,()->s.deposit(lord,1));
        JsonObject state=JsonParser.parseString(Files.readString(file())).getAsJsonObject();state.getAsJsonArray("progress").get(0).getAsJsonObject().addProperty("level",4294967296L);Files.writeString(file(),state.toString());assertThrows(java.io.IOException.class,this::load);
    }
}
