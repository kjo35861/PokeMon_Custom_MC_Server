package space.pocketmate.estates;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import com.google.gson.*;
import static org.junit.jupiter.api.Assertions.*;

class EstateCommunityTest {
    @TempDir Path root;
    final UUID lord=UUID.randomUUID(),alice=UUID.randomUUID(),bob=UUID.randomUUID();
    ClaimStore store() throws Exception{return new ClaimStore(root.resolve("ownership.json"));}
    ClaimStore village() throws Exception {
        ClaimStore store=store();store.createEstate(lord,"Lord","달빛 마을",0,0);store.seen(lord,"Lord",100);store.seen(alice,"Alice",200);store.seen(bob,"Bob",300);return store;
    }
    void join(ClaimStore store,UUID id) throws Exception{store.invite(lord,id);store.answerInvite(id,lord,true);}
    void blockSave() throws Exception{Path file=root.resolve("ownership.json");Files.move(file,root.resolve("before.json"));Files.createDirectory(file);Files.writeString(file.resolve("blocker"),"block");}
    @Test void namedCreationPersistsWithOwnership() throws Exception {
        ClaimStore s=village();assertEquals("달빛 마을",store().estateFor(lord).name());assertEquals(ClaimStore.Role.LORD,s.estateFor(lord).members().getFirst().role());assertEquals(lord,store().get(0,0).owner());
    }
    @Test void invalidNamesNeverCreateOwnership() throws Exception {
        ClaimStore s=store();for(String name:List.of("   ","a".repeat(25),"a\nb","<script>"))assertThrows(ClaimStore.Denied.class,()->s.createEstate(lord,"Lord",name,0,0));assertNull(s.get(0,0));
    }
    @Test void invitationNeedsAcceptanceAndCanBeDeclined() throws Exception {
        ClaimStore s=village();s.invite(lord,alice);assertNull(s.estateFor(alice));assertEquals(1,store().invitationsFor(alice).size());
        s.answerInvite(alice,lord,false);assertTrue(s.invitationsFor(alice).isEmpty());s.invite(lord,alice);s.answerInvite(alice,lord,true);assertEquals(ClaimStore.Role.RESIDENT,store().estateFor(alice).members().get(1).role());
    }
    @Test void onlyLordMayManageAndLordCannotBeReplacedOrKicked() throws Exception {
        ClaimStore s=village();join(s,alice);s.changeRole(lord,alice,ClaimStore.Role.STEWARD);
        assertThrows(ClaimStore.Denied.class,()->s.invite(alice,bob));assertThrows(ClaimStore.Denied.class,()->s.kick(alice,lord));
        assertThrows(ClaimStore.Denied.class,()->s.changeRole(alice,bob,ClaimStore.Role.RESIDENT));assertThrows(ClaimStore.Denied.class,()->s.updateNotice(alice,"notice"));
        assertThrows(ClaimStore.Denied.class,()->s.updateImage(alice,""));assertThrows(ClaimStore.Denied.class,()->s.deleteEstate(alice,"달빛 마을"));
        assertThrows(ClaimStore.Denied.class,()->s.changeRole(lord,alice,ClaimStore.Role.LORD));assertThrows(ClaimStore.Denied.class,()->s.changeRole(lord,lord,ClaimStore.Role.RESIDENT));assertThrows(ClaimStore.Denied.class,()->s.kick(lord,lord));
        s.changeRole(lord,alice,ClaimStore.Role.RESIDENT);s.kick(lord,alice);assertNull(store().estateFor(alice));assertEquals(1,s.estateFor(lord).members().size());
    }
    @Test void cannotJoinTwoEstatesOrOwnAnotherAsMember() throws Exception {
        ClaimStore s=village();join(s,alice);assertThrows(ClaimStore.Denied.class,()->s.createEstate(alice,"Alice","새 마을",10,10));
        s.createEstate(bob,"Bob","다른 마을",10,10);assertThrows(ClaimStore.Denied.class,()->s.invite(bob,alice));
    }
    @Test void forgedDuplicateExpiredAndUnknownInvitationsFail() throws Exception {
        ClaimStore s=village();assertThrows(ClaimStore.Denied.class,()->s.answerInvite(alice,lord,true));assertThrows(ClaimStore.Denied.class,()->s.invite(lord,UUID.randomUUID()));
        s.invite(lord,alice);assertThrows(ClaimStore.Denied.class,()->s.invite(lord,alice));assertThrows(ClaimStore.Denied.class,()->s.answerInvite(bob,lord,true));
        Path path=root.resolve("ownership.json");JsonObject json=JsonParser.parseString(Files.readString(path)).getAsJsonObject();json.getAsJsonArray("estates").get(0).getAsJsonObject().getAsJsonArray("invitations").get(0).getAsJsonObject().addProperty("at",0);Files.writeString(path,json.toString());
        assertThrows(ClaimStore.Denied.class,()->store().answerInvite(alice,lord,true));
    }
    @Test void announcementAndImageValidationPersist() throws Exception {
        ClaimStore s=village();s.updateNotice(lord,"환영합니다\n함께해요");assertEquals("환영합니다\n함께해요",store().estateFor(lord).announcement());assertThrows(ClaimStore.Denied.class,()->s.updateNotice(lord,"x".repeat(1001)));
        assertThrows(ClaimStore.Denied.class,()->s.updateImage(lord,"https://example.com/track.jpg"));assertThrows(ClaimStore.Denied.class,()->s.updateImage(lord,"data:image/jpeg;base64,broken"));
        var image=new java.awt.image.BufferedImage(16,9,java.awt.image.BufferedImage.TYPE_INT_RGB);var bytes=new java.io.ByteArrayOutputStream();javax.imageio.ImageIO.write(image,"jpeg",bytes);
        String encoded="data:image/jpeg;base64,"+Base64.getEncoder().encodeToString(bytes.toByteArray());s.updateImage(lord,encoded);assertEquals(encoded,store().estateFor(lord).image());
    }
    @Test void deleteRequiresExactNameAndReleasesOnlyItsOwnClaims() throws Exception {
        ClaimStore s=village();join(s,alice);s.upgrade(lord,0);s.buyBatch(lord,"Lord",List.of(new ClaimStore.Key(1,0)));s.createEstate(bob,"Bob","다른 마을",10,10);
        assertThrows(ClaimStore.Denied.class,()->s.deleteEstate(lord,"달빛마을"));assertThrows(ClaimStore.Denied.class,()->s.deleteEstate(lord,"달빛 마을 "));assertEquals(2,s.owned(lord).size());
        s.deleteEstate(lord,"달빛 마을");ClaimStore restored=store();assertNull(restored.estateFor(lord));assertNull(restored.estateFor(alice));assertNull(restored.get(0,0));assertNull(restored.get(1,0));assertNotNull(restored.estateFor(bob));assertEquals(bob,restored.get(10,10).owner());
    }
    @Test void failedManagementAndDeletionSaveLeaveStateUnchanged() throws Exception {
        ClaimStore s=village();s.invite(lord,alice);blockSave();assertThrows(java.io.IOException.class,()->s.answerInvite(alice,lord,true));assertNull(s.estateFor(alice));assertEquals(1,s.invitationsFor(alice).size());
        assertThrows(java.io.IOException.class,()->s.updateNotice(lord,"changed"));assertEquals("",s.estateFor(lord).announcement());
        assertThrows(java.io.IOException.class,()->s.deleteEstate(lord,"달빛 마을"));assertNotNull(s.estateFor(lord));assertNotNull(s.get(0,0));
    }
    @Test void legacyWorldMigratesWithoutLosingClaims() throws Exception {
        ClaimStore s=village();Path path=root.resolve("ownership.json");JsonObject json=JsonParser.parseString(Files.readString(path)).getAsJsonObject();json.addProperty("formatVersion",1);json.remove("estates");json.remove("players");Files.writeString(path,json.toString());
        ClaimStore migrated=store();assertEquals("Lord의 영지",migrated.estateFor(lord).name());assertEquals(lord,migrated.get(0,0).owner());migrated.seen(lord,"Lord",500);assertNotNull(store().estateFor(lord));assertTrue(Files.readString(path).contains("\"formatVersion\": 3"));
    }
    @Test void damagedCommunityDataCannotResetWorld() throws Exception {
        village();Path path=root.resolve("ownership.json");JsonObject json=JsonParser.parseString(Files.readString(path)).getAsJsonObject();json.remove("estates");Files.writeString(path,json.toString());assertThrows(java.io.IOException.class,this::store);
    }
    @Test void knownPlayersLastSeenSurvivesReload() throws Exception {
        ClaimStore s=village();s.seen(alice,"AliceNew",999);assertEquals(999,store().known(alice).lastSeen());assertEquals("AliceNew",store().known(alice).name());
    }
}
