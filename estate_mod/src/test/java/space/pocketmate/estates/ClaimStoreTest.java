package space.pocketmate.estates;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;

class ClaimStoreTest {
    @TempDir Path root;
    final UUID a=UUID.randomUUID(),b=UUID.randomUUID();
    ClaimStore store() throws Exception{return new ClaimStore(root.resolve("ownership.json"));}
    ClaimStore.Claim created(ClaimStore s,UUID owner,String name,int x,int z) throws Exception {
        ClaimStore.Claim claim=s.buy(owner,name,x,z,true);s.creditTreasury(owner,8_000_000,owner,true);for(int level=0;level<10;level++)s.upgrade(owner,level);return claim;
    }
    @Test void firstClaimPersistsAndReloads() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",-1,-2);
        assertEquals(a,store().get(-1,-2).owner());assertEquals(1,store().owned(a).size());
    }
    @Test void cannotStealOrRebuy() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);
        assertEquals(ClaimStore.Failure.OCCUPIED,assertThrows(ClaimStore.Rejected.class,()->created(s,b,"Bob",0,0)).reason);
        assertThrows(ClaimStore.Rejected.class,()->s.buy(a,"Alice",0,0,false));assertEquals(a,store().get(0,0).owner());
    }
    @Test void onlyCardinalNeighborsCanExpand() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);
        assertEquals(ClaimStore.Failure.NOT_ADJACENT,assertThrows(ClaimStore.Rejected.class,()->s.buy(a,"Alice",1,1,false)).reason);
        s.buy(a,"Alice",1,0,false);s.buy(a,"Alice",2,0,false);s.buy(a,"Alice",2,-1,false);
        assertEquals(4,s.owned(a).size());
    }
    @Test void anotherOwnersNeighborDoesNotCount() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);created(s,b,"Bob",5,5);
        assertThrows(ClaimStore.Rejected.class,()->s.buy(a,"Alice",6,5,false));
    }
    @Test void cannotCreateDisconnectedSecondEstate() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);
        assertEquals(ClaimStore.Failure.ALREADY_HAS_ESTATE,assertThrows(ClaimStore.Rejected.class,()->created(s,a,"Alice",10,10)).reason);
        assertEquals(ClaimStore.Failure.NO_ESTATE,assertThrows(ClaimStore.Rejected.class,()->s.buy(b,"Bob",1,0,false)).reason);
    }
    @Test void simultaneousFirstPurchasesHaveOneWinner() throws Exception {
        ClaimStore s=store();ExecutorService pool=Executors.newFixedThreadPool(2);CountDownLatch go=new CountDownLatch(1);
        try{
            List<Future<Boolean>> results=new ArrayList<>();for(UUID owner:List.of(a,b))results.add(pool.submit(()->{go.await();try{created(s,owner,"Player",3,3);return true;}catch(ClaimStore.Rejected rejection){return false;}}));
            go.countDown();int wins=0;for(Future<Boolean> future:results)if(future.get())wins++;assertEquals(1,wins);assertNotNull(store().get(3,3));
        }finally{pool.shutdownNow();}
    }
    @Test void failedSaveNeverChangesOwnership() throws Exception {
        Path blocker=root.resolve("blocked");Files.writeString(blocker,"not a folder");ClaimStore s=new ClaimStore(blocker.resolve("ownership.json"));
        assertThrows(java.io.IOException.class,()->created(s,a,"Alice",0,0));assertNull(s.get(0,0));
    }
    @Test void corruptOrDuplicateFilesFailClosed() throws Exception {
        Path path=root.resolve("ownership.json");Files.writeString(path,"broken json");assertThrows(java.io.IOException.class,this::store);
        Files.delete(path);ClaimStore s=store();created(s,a,"Alice",0,0);
        com.google.gson.JsonObject json=com.google.gson.JsonParser.parseString(Files.readString(path)).getAsJsonObject();
        json.getAsJsonArray("claims").add(json.getAsJsonArray("claims").get(0).deepCopy());
        Files.writeString(path,json.toString());assertThrows(java.io.IOException.class,this::store);
    }
    @Test void coordinatesAreBoundedAndNegativeNeighborsWork() throws Exception {
        ClaimStore s=store();assertThrows(ClaimStore.Rejected.class,()->created(s,a,"Alice",Integer.MAX_VALUE,0));
        created(s,a,"Alice",-2,-2);s.buy(a,"Alice",-3,-2,false);assertEquals(2,s.owned(a).size());
    }
    @Test void incompleteFilesCannotSilentlyResetOwnership() throws Exception {
        Path path=root.resolve("ownership.json");
        for(String content:List.of("{}","{\"formatVersion\":1,\"dimension\":\"minecraft:overworld\"}",
            "{\"formatVersion\":1,\"dimension\":\"minecraft:overworld\",\"claims\":[{}]}")) {
            Files.writeString(path,content);assertThrows(java.io.IOException.class,this::store);
        }
    }
    @Test void batchCanConnectThroughOtherSelectedChunksInAnyOrder() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);
        s.buyBatch(a,"Alice",List.of(new ClaimStore.Key(3,0),new ClaimStore.Key(2,0),new ClaimStore.Key(1,0),new ClaimStore.Key(3,1)));
        assertEquals(5,store().owned(a).size());
    }
    @Test void disconnectedBatchIsRejectedWithoutPartialPurchase() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);String before=Files.readString(root.resolve("ownership.json"));
        assertEquals(ClaimStore.Failure.NOT_ADJACENT,assertThrows(ClaimStore.Rejected.class,()->
            s.buyBatch(a,"Alice",List.of(new ClaimStore.Key(1,0),new ClaimStore.Key(3,0)))).reason);
        assertNull(s.get(1,0));assertEquals(before,Files.readString(root.resolve("ownership.json")));
        assertThrows(ClaimStore.Rejected.class,()->s.buyBatch(a,"Alice",List.of(new ClaimStore.Key(1,0),new ClaimStore.Key(2,1))));
        assertEquals(1,s.owned(a).size());
    }
    @Test void occupiedBatchNeverPurchasesItsUnoccupiedPart() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);created(s,b,"Bob",2,0);
        assertEquals(ClaimStore.Failure.OCCUPIED,assertThrows(ClaimStore.Rejected.class,()->
            s.buyBatch(a,"Alice",List.of(new ClaimStore.Key(1,0),new ClaimStore.Key(2,0)))).reason);
        assertNull(s.get(1,0));assertEquals(b,s.get(2,0).owner());
    }
    @Test void duplicateEmptyAndOversizedBatchesAreRejected() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);ClaimStore.Key neighbor=new ClaimStore.Key(1,0);
        for(List<ClaimStore.Key> chunks:List.of(List.<ClaimStore.Key>of(),List.of(neighbor,neighbor),
            java.util.stream.IntStream.rangeClosed(1,129).mapToObj(x->new ClaimStore.Key(x,0)).toList()))
            assertEquals(ClaimStore.Failure.INVALID_SELECTION,assertThrows(ClaimStore.Rejected.class,()->s.buyBatch(a,"Alice",chunks)).reason);
        assertEquals(1,s.owned(a).size());
    }
    @Test void failedBatchSaveNeverUpdatesMemory() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);Path path=root.resolve("ownership.json");
        Files.move(path,root.resolve("original.json"));Files.createDirectory(path);Files.writeString(path.resolve("blocker"),"block");
        assertThrows(java.io.IOException.class,()->s.buyBatch(a,"Alice",List.of(new ClaimStore.Key(1,0),new ClaimStore.Key(2,0))));
        assertNull(s.get(1,0));assertNull(s.get(2,0));assertEquals(1,s.owned(a).size());
    }
    @Test void competingBatchesHaveOneWholeWinner() throws Exception {
        ClaimStore s=store();created(s,a,"Alice",0,0);created(s,b,"Bob",3,0);
        List<ClaimStore.Key> chunks=List.of(new ClaimStore.Key(1,0),new ClaimStore.Key(2,0));
        ExecutorService pool=Executors.newFixedThreadPool(2);CountDownLatch go=new CountDownLatch(1);
        try{
            List<Future<Boolean>> results=new ArrayList<>();for(UUID owner:List.of(a,b))results.add(pool.submit(()->{
                go.await();try{s.buyBatch(owner,"Player",chunks);return true;}catch(ClaimStore.Rejected rejected){return false;}
            }));
            go.countDown();int wins=0;for(Future<Boolean> result:results)if(result.get())wins++;
            assertEquals(1,wins);assertEquals(s.get(1,0).owner(),s.get(2,0).owner());assertEquals(4,store().owned(a).size()+store().owned(b).size());
        }finally{pool.shutdownNow();}
    }
}
