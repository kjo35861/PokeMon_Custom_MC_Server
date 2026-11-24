package space.pocketmate.estates;
import net.minecraft.registry.Registries;
import net.minecraft.stat.StatHandler;
import net.minecraft.stat.Stats;
import net.minecraft.util.Identifier;
import java.util.List;

/** Custom-stat registry values must be canonical registry objects, not freshly constructed IDs. */
public final class MissionStatistics {
 private MissionStatistics() {}
 public static List<Identifier> walking(){return List.of(Stats.WALK_ONE_CM,Stats.SPRINT_ONE_CM,Stats.CROUCH_ONE_CM);}
 public static List<Identifier> otherTravel(){return List.of(Stats.SWIM_ONE_CM,Stats.WALK_ON_WATER_ONE_CM,Stats.WALK_UNDER_WATER_ONE_CM,Stats.BOAT_ONE_CM,Stats.HORSE_ONE_CM,Stats.PIG_ONE_CM,Stats.STRIDER_ONE_CM);}
 public static int custom(StatHandler handler,Identifier key){
  if(key==null)return 0;
  Identifier registered=Registries.CUSTOM_STAT.get(key);
  if(registered==null)return 0;
  return handler.getStat(Stats.CUSTOM.getOrCreateStat(registered));
 }
 public static long centimeters(StatHandler handler,List<Identifier> stats){long total=0;for(Identifier key:stats)total+=custom(handler,key);return total;}
}
