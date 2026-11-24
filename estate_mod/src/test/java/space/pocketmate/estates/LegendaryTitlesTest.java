package space.pocketmate.estates;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Path;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class LegendaryTitlesTest {
 @TempDir Path root;
 @Test void grantsAllTitlesOnceAndPreservesEquipmentAndOtherPlayers() throws Exception {
  var file=root.resolve("all.json");var store=new ProfileStore(file);UUID user=UUID.randomUUID(),other=UUID.randomUUID();
  store.grant(user,"icon","pikachu");store.equip(user,"pikachu","beginner","night");var before=store.get(user);var otherBefore=store.get(other);
  int expected=(int)ProfileStore.CATALOG.stream().filter(c->c.kind().equals("title")&&!before.owned().contains("title:"+c.id())).count();
  assertEquals(expected,store.grantAllTitles(user));assertEquals(0,store.grantAllTitles(user));
  var saved=new ProfileStore(file);assertEquals("pikachu",saved.get(user).icon());assertEquals("beginner",saved.get(user).title());assertEquals("night",saved.get(user).banner());
  for(var item:ProfileStore.CATALOG)if(item.kind().equals("title"))assertTrue(saved.get(user).owned().contains("title:"+item.id()));
  assertEquals(otherBefore,saved.get(other));assertFalse(saved.get(user).owned().contains("icon:eevee"));
 }
 @Test void everyRewardRequiresGrantAndPersistsWithItsOwnGlyph() throws Exception {
  var entries=LegendaryTitles.entries();assertEquals(94,entries.size());
  Set<String> ids=new HashSet<>(),glyphs=new HashSet<>();UUID user=UUID.randomUUID();
  var store=new ProfileStore(root.resolve("profiles.json"));
  for(var title:entries){
   assertTrue(ids.add(title.id()));assertTrue(glyphs.add(title.glyph()));
   assertFalse(title.starter());assertEquals("pocketmate:legendary_titles",title.font());
   assertEquals(1,title.glyph().length());assertTrue(title.color().matches("#[0-9A-Fa-f]{6}"));
   assertThrows(ProfileStore.Denied.class,()->store.equip(user,"skin",title.id(),"none"));
   store.grant(user,"title",title.id());store.equip(user,"skin",title.id(),"none");
   assertEquals(title.id(),new ProfileStore(root.resolve("profiles.json")).equippedTitle(user));
  }
  assertEquals(94,store.get(user).owned().stream().filter(k->k.startsWith("title:legendary_")).count());
 }
}
