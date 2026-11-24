package space.pocketmate.estates;

import com.google.gson.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class EstateHomeTest {
    @TempDir Path root;
    final UUID lord=UUID.randomUUID(),member=UUID.randomUUID(),other=UUID.randomUUID();
    Path file(){return root.resolve("estates.json");}
    ClaimStore load() throws Exception{return new ClaimStore(file());}
    ClaimStore.Home point(){return new ClaimStore.Home(-5.25,68,35.75,45,10,false);}
    ClaimStore fresh() throws Exception{var s=load();s.createEstate(lord,"Lord","마을",-1,2,point());return s;}
    void join(ClaimStore s) throws Exception{s.seen(member,"Member",1);s.invite(lord,member);s.answerInvite(member,lord,true);}
    @Test void initialHomePersistsExactCreationPositionAndOrientation() throws Exception {
        var s=fresh();assertEquals(point(),s.homeFor(lord));assertEquals(point(),load().homeFor(lord));
        var json=JsonParser.parseString(Files.readString(file())).getAsJsonObject();assertEquals(4,json.get("formatVersion").getAsInt());assertEquals("minecraft:overworld",json.get("dimension").getAsString());
    }
    @Test void onlyLordMaySetButMembersMayResolveHome() throws Exception {
        var s=fresh();join(s);s.changeRole(lord,member,ClaimStore.Role.STEWARD);
        assertEquals(point(),s.homeFor(member));assertThrows(ClaimStore.Denied.class,()->s.homeFor(other));
        assertThrows(ClaimStore.Denied.class,()->s.setHome(member,point()));assertThrows(ClaimStore.Denied.class,()->s.setHome(other,point()));assertEquals(point(),load().homeFor(lord));
    }
    @Test void homeMustStayInsideOwnedTerritoryIncludingNegativeCoordinates() throws Exception {
        var s=fresh();s.createEstate(other,"Other","다른 마을",0,2);
        String before=Files.readString(file());assertThrows(ClaimStore.Denied.class,()->s.setHome(lord,new ClaimStore.Home(.5,68,35,0,0,false)));assertThrows(ClaimStore.Denied.class,()->s.setHome(lord,new ClaimStore.Home(-16.01,68,35,0,0,false)));assertEquals(before,Files.readString(file()));
        var next=new ClaimStore.Home(-.01,70,40,170,-20,false);s.setHome(lord,next);assertEquals(next,load().homeFor(lord));
    }
    @Test void invalidPositionsAndCreationMismatchNeverPersist() throws Exception {
        var s=fresh();String before=Files.readString(file());
        for(var h:List.of(new ClaimStore.Home(Double.NaN,68,35,0,0,false),new ClaimStore.Home(-5,Double.POSITIVE_INFINITY,35,0,0,false),new ClaimStore.Home(-5,320,35,0,0,false),new ClaimStore.Home(-5,68,35,0,100,false),new ClaimStore.Home(-5,68,35,0,0,true)))assertThrows(ClaimStore.Denied.class,()->s.setHome(lord,h));
        assertEquals(before,Files.readString(file()));assertThrows(ClaimStore.Denied.class,()->s.createEstate(other,"Other","다른 마을",3,3,point()));assertNull(s.estateFor(other));
    }
    @Test void homeSurvivesUnrelatedEstateAndEconomyChanges() throws Exception {
        var s=fresh();var next=new ClaimStore.Home(-3,70,38,90,0,false);s.setHome(lord,next);join(s);s.updateNotice(lord,"공지");s.updateImage(lord,"");s.creditWallet(lord,100);s.deposit(lord,100);s.upgrade(lord,0);s.kick(lord,member);
        assertEquals(next,load().homeFor(lord));assertEquals(100,load().progress(lord).treasury());assertEquals(1,load().owned(lord).size());
    }
    @Test void failedSavePreservesPreviousHome() throws Exception {
        var s=fresh();Files.move(file(),root.resolve("before.json"));Files.createDirectory(file());Files.writeString(file().resolve("blocker"),"block");
        assertThrows(java.io.IOException.class,()->s.setHome(lord,new ClaimStore.Home(-2,72,39,0,0,false)));assertEquals(point(),s.homeFor(lord));
    }
    @Test void legacyV3UsesEarliestClaimWithoutResettingLandOrWallet() throws Exception {
        var s=fresh();s.upgrade(lord,0);s.buyBatch(lord,"Lord",List.of(new ClaimStore.Key(0,2)));s.creditWallet(lord,1234);
        var json=JsonParser.parseString(Files.readString(file())).getAsJsonObject();json.addProperty("formatVersion",3);json.getAsJsonArray("estates").get(0).getAsJsonObject().remove("home");Files.writeString(file(),json.toString());
        var migrated=load();var h=migrated.homeFor(lord);assertTrue(h.surface());assertEquals(-7.5,h.x());assertEquals(40.5,h.z());assertEquals(2,migrated.owned(lord).size());assertEquals(1234,migrated.wallet(lord));migrated.seen(lord,"Lord",1);assertEquals(h,load().homeFor(lord));
    }
    @Test void missingOrForeignHomeFailsClosedAndDeletionRemovesAccess() throws Exception {
        var s=fresh();String original=Files.readString(file());
        for(String field:List.of("x","y","z","yaw","pitch","surface")){
            var json=JsonParser.parseString(original).getAsJsonObject();json.getAsJsonArray("estates").get(0).getAsJsonObject().getAsJsonObject("home").remove(field);Files.writeString(file(),json.toString());assertThrows(java.io.IOException.class,this::load);
        }
        Files.writeString(file(),original);var json=JsonParser.parseString(original).getAsJsonObject();json.getAsJsonArray("estates").get(0).getAsJsonObject().getAsJsonObject("home").addProperty("x",25);Files.writeString(file(),json.toString());assertThrows(java.io.IOException.class,this::load);
        Files.writeString(file(),original);s=load();s.deleteEstate(lord,"마을");var deleted=load();assertThrows(ClaimStore.Denied.class,()->deleted.homeFor(lord));
    }
}
