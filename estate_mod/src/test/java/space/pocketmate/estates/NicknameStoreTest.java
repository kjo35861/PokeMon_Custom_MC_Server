package space.pocketmate.estates;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class NicknameStoreTest {
 @TempDir Path root;UUID a=UUID.randomUUID(),b=UUID.randomUUID();
 NicknameStore store()throws Exception{return new NicknameStore(root.resolve("names.json"));}
 @Test void koreanPersistsAndResolvesByUuid()throws Exception{var s=store();s.register(a,"포켓친구",Map.of());assertEquals("포켓친구",store().get(a));assertEquals(a,store().resolve("포켓친구"));}
 @Test void duplicateAndSecondRegistrationFail()throws Exception{var s=store();s.register(a,"Trainer",Map.of());assertThrows(IllegalArgumentException.class,()->s.register(b,"trainer",Map.of()));assertThrows(IllegalArgumentException.class,()->s.register(a,"다른이름",Map.of()));assertEquals("Trainer",store().get(a));}
 @Test void invalidCharactersAreRejected(){for(String name:List.of("a","가","가 나","관리자§a","@s","../닉네임","이름\n","가나다라마바사아자차카타파","😀친구"," 이름"))assertThrows(IllegalArgumentException.class,()->NicknameStore.normalize(name),name);}
 @Test void knownAccountNamesCannotBeImpersonated()throws Exception{var s=store();assertThrows(IllegalArgumentException.class,()->s.register(a,"Player",Map.of(b,"player")));s.register(a,"Player",Map.of(a,"Player"));assertEquals(a,s.resolve("PLAYER"));}
 @Test void corruptStoreRefusesReset()throws Exception{Files.writeString(root.resolve("names.json"),"{}");assertThrows(java.io.IOException.class,this::store);}
 @Test void failedSavePreservesMemory()throws Exception{var s=store();Files.createDirectory(root.resolve("names.json"));Files.writeString(root.resolve("names.json/block"),"x");assertThrows(java.io.IOException.class,()->s.register(a,"모험친구",Map.of()));assertNull(s.get(a));}
 @Test void lookupsNeverCreateFile()throws Exception{var s=store();assertNull(s.get(a));assertNull(s.resolve("이름없음"));assertFalse(Files.exists(root.resolve("names.json")));}
}
