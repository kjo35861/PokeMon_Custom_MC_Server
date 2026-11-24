package space.pocketmate.estates;
import java.io.IOException;
import java.util.*;
/** Loader-neutral contract for the future NeoForge Pixelmon listener. No event bus is subscribed on Fabric. */
public final class PixelmonMissionSignals {
 private PixelmonMissionSignals() {}
 public static void captured(MissionStore store,UUID player,UUID pokemon,String species,boolean wild) throws IOException {
  if(!wild)return;validate(species);
  store.event(player,Map.of("capture",1,"capture_species",1),species,"capture:"+pokemon);
 }
 public static void defeated(MissionStore store,UUID player,UUID battle,UUID pokemon,String species,boolean wild) throws IOException {
  if(!wild)return;validate(species);
  store.event(player,Map.of("defeat",1,"defeat_species",1),species,"defeat:"+battle+":"+pokemon);
 }
 public static void wonBattle(MissionStore store,UUID player,UUID battle,boolean wild,boolean captureEnd) throws IOException {
  if(!wild||captureEnd)return;
  store.event(player,Map.of("battle_win",1),null,"victory:"+battle);
 }
 private static void validate(String species){if(species==null||!species.matches("[a-z0-9_:-]{1,80}"))throw new IllegalArgumentException("Use a species registry ID, never a nickname");}
}
