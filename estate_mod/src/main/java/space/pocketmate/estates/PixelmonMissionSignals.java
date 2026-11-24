package space.pocketmate.estates;
import java.io.IOException;
import java.time.Instant;
import java.util.*;
/** Contract for the future NeoForge listener. Natural origin must be established by trusted server spawn hooks. */
public final class PixelmonMissionSignals {
 public enum Origin { NATURAL, PLAYER_OWNED, COMMAND, SPAWNER, RAID, UNKNOWN }
 public record Encounter(boolean wild,Origin origin) {public boolean eligible(){return wild&&origin==Origin.NATURAL;}}
 private PixelmonMissionSignals() {}
 public static void captured(MissionStore store,UUID player,UUID pokemon,String species,Encounter encounter,Instant completedAt) throws IOException {
  if(encounter==null||!encounter.eligible())return;validate(species);
  store.eventAt(player,Map.of("capture",1,"capture_species",1),species,"capture:"+pokemon,completedAt);
 }
 public static void defeated(MissionStore store,UUID player,UUID battle,UUID pokemon,String species,Encounter encounter,Instant completedAt) throws IOException {
  if(encounter==null||!encounter.eligible())return;validate(species);
  store.eventAt(player,Map.of("defeat",1,"defeat_species",1),species,"defeat:"+pokemon,completedAt);
 }
 public static void wonBattle(MissionStore store,UUID player,UUID battle,Collection<Encounter> opponents,boolean pvp,boolean captureEnd,Instant completedAt) throws IOException {
  if(pvp||captureEnd||opponents==null||opponents.isEmpty()||opponents.stream().anyMatch(e->e==null||!e.eligible()))return;
  store.eventAt(player,Map.of("battle_win",1),null,"victory:"+battle,completedAt);
 }
 private static void validate(String species){if(species==null||!species.matches("[a-z0-9_:-]{1,80}"))throw new IllegalArgumentException("Use a species registry ID, never a nickname");}
}
