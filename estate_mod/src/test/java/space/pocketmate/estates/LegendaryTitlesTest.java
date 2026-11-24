package space.pocketmate.estates;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Path;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class LegendaryTitlesTest {
 @TempDir Path root;
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
