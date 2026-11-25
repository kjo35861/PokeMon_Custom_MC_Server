package space.pocketmate.estates;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class ProfileStoreTest {
    @TempDir Path root;
    final UUID alice=UUID.randomUUID(),bob=UUID.randomUUID();
    Path file(){return root.resolve("profiles.json");}
    ProfileStore store() throws Exception{return new ProfileStore(file());}
    @Test void firstCaptureHasOneWinnerAcrossRestarts() throws Exception {
        var profiles=store();
        assertTrue(profiles.firstCapture(alice,144));
        assertFalse(profiles.firstCapture(alice,25));
        var reopened=store();
        assertFalse(reopened.firstCapture(bob,144));
        assertTrue(reopened.get(alice).owned().contains("title:legendary_144"));
        assertFalse(reopened.get(bob).owned().contains("title:legendary_144"));
    }
    @Test void managedTitlesPersistAndDeletingUnequipsForEveryPlayer() throws Exception {
        var s=store();
        s.editTitle("trail","숲길 안내자","#12ab34","none",true);
        s.grant(alice,"title","trail");
        s.equip(alice,"skin","trail","none");
        s.editTitle("trail","숲의 안내자","#abc123","keep",false);
        s=store();
        assertEquals("trail",s.equippedTitle(alice));
        assertEquals("#abc123",s.cosmetic("title","trail").color());
        assertEquals("",s.cosmetic("title","trail").glyph());
        s.deleteTitle("trail");
        s.deleteTitle("beginner");
        s=store();
        assertNull(s.cosmetic("title","trail"));
        assertNull(s.cosmetic("title","beginner"));
        assertEquals("none",s.equippedTitle(alice));
        assertFalse(s.get(alice).owned().contains("title:trail"));
        assertEquals("none",s.get(bob).title());
    }
    @Test void starterOwnershipAndDefaultsPersist() throws Exception {
        var profile=store().get(alice);assertEquals("skin",profile.icon());assertEquals("beginner",profile.title());assertEquals("none",profile.banner());
        assertTrue(profile.owned().contains("banner:forest"));assertFalse(profile.owned().contains("icon:pikachu"));assertEquals(profile,store().get(alice));
    }
    @Test void equipsOwnedItemsTogetherAndKeepsOtherPlayer() throws Exception {
        var s=store();var other=s.get(bob);s.equip(alice,"bulbasaur","none","night");
        var saved=store().get(alice);assertEquals("bulbasaur",saved.icon());assertEquals("none",saved.title());assertEquals("night",saved.banner());assertEquals(other,store().get(bob));
    }
    @Test void lockedOrWrongKindRejectsWholeEquipmentChange() throws Exception {
        var s=store();var original=s.get(alice);byte[] before=Files.readAllBytes(file());
        assertThrows(ProfileStore.Denied.class,()->s.equip(alice,"pikachu","none","forest"));
        assertThrows(ProfileStore.Denied.class,()->s.equip(alice,"bulbasaur","beginner","skin"));
        assertThrows(ProfileStore.Denied.class,()->s.equip(alice,"https://example.com","none","forest"));
        assertEquals(original,s.get(alice));assertArrayEquals(before,Files.readAllBytes(file()));
    }
    @Test void grantIsPersistentAndBelongsOnlyToRecipient() throws Exception {
        var s=store();s.grant(alice,"icon","pikachu");s.grant(alice,"icon","pikachu");s.equip(alice,"pikachu","beginner","none");
        assertEquals("pikachu",store().get(alice).icon());assertFalse(s.get(bob).owned().contains("icon:pikachu"));
        assertThrows(ProfileStore.Denied.class,()->s.grant(alice,"title","not-real"));
    }
    @Test void failedWriteDoesNotChangeEquipmentOrOwnership() throws Exception {
        var s=store();var before=s.get(alice);Files.move(file(),root.resolve("saved.json"));Files.createDirectory(file());Files.writeString(file().resolve("blocker"),"block");
        assertThrows(IOException.class,()->s.equip(alice,"bulbasaur","none","night"));assertEquals(before,s.get(alice));
        assertThrows(IOException.class,()->s.grant(alice,"icon","pikachu"));assertEquals(before,s.get(alice));
    }
    @Test void corruptedStoreCannotResetOwnership() throws Exception {
        Files.writeString(file(),"{}");assertThrows(IOException.class,this::store);assertEquals("{}",Files.readString(file()));
    }
    @Test void chatTitleLookupTracksEquipmentWithoutWriting() throws Exception {
        var s=store();assertEquals("beginner",s.equippedTitle(alice));assertFalse(Files.exists(file()));
        s.equip(alice,"skin","none","none");byte[] before=Files.readAllBytes(file());
        assertEquals("none",s.equippedTitle(alice));assertEquals("beginner",s.equippedTitle(bob));
        assertArrayEquals(before,Files.readAllBytes(file()));
        s.equip(alice,"skin","beginner","none");assertEquals("beginner",store().equippedTitle(alice));
    }
    @Test void publicLookupsDoNotCreateOrWriteProfiles() throws Exception {
        var s=store();var appearance=s.appearance(alice);
        assertEquals("skin",appearance.icon());assertEquals("none",appearance.banner());assertFalse(Files.exists(file()));
        s.get(alice);byte[] before=Files.readAllBytes(file());s.appearance(bob);assertArrayEquals(before,Files.readAllBytes(file()));
    }
    @Test void publicAppearanceUsesEachPlayersSavedEquipmentOnly() throws Exception {
        var s=store();s.equip(alice,"bulbasaur","none","night");s.equip(bob,"charmander","beginner","forest");
        var a=store().appearance(alice);var b=store().appearance(bob);
        assertEquals("./profile-assets/bulbasaur.png",a.iconImage());assertEquals("./profile-assets/night.svg",a.bannerImage());
        assertEquals("charmander",b.icon());assertEquals("forest",b.banner());
        var json=new com.google.gson.Gson().toJsonTree(a).getAsJsonObject();
        assertEquals(Set.of("icon","iconImage","banner","bannerImage"),json.keySet());assertFalse(json.has("owned"));
    }
}
