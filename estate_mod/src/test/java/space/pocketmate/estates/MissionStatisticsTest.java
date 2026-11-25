package space.pocketmate.estates;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import net.minecraft.SharedConstants;
import net.minecraft.Bootstrap;
import net.minecraft.registry.Registries;
import net.minecraft.stat.StatHandler;
import net.minecraft.stat.Stats;
import net.minecraft.util.Identifier;
import static org.junit.jupiter.api.Assertions.*;

/** Initializes vanilla registries only. Does not launch Minecraft, create a server or load a world. */
class MissionStatisticsTest {
 @BeforeAll static void registryBootstrap(){SharedConstants.createGameVersion();Bootstrap.initialize();}
 @Test void registeredConstantsAndEquivalentNewIdsReadWithoutCrashing(){
  var stats=new StatHandler();stats.setStat(null,Stats.CUSTOM.getOrCreateStat(Stats.FISH_CAUGHT),3);
  assertEquals(3,MissionStatistics.custom(stats,Stats.FISH_CAUGHT));
  assertEquals(3,MissionStatistics.custom(stats,Identifier.ofVanilla("fish_caught")));
  for(var id:MissionStatistics.walking()){assertTrue(Registries.CUSTOM_STAT.containsId(id));assertDoesNotThrow(()->MissionStatistics.custom(stats,id));}
  for(var id:MissionStatistics.otherTravel()){assertTrue(Registries.CUSTOM_STAT.containsId(id));assertDoesNotThrow(()->MissionStatistics.custom(stats,id));}
 }
 @Test void unknownOrMissingStatisticIsIgnored(){
  var stats=new StatHandler();assertEquals(0,MissionStatistics.custom(stats,null));assertEquals(0,MissionStatistics.custom(stats,Identifier.of("pocketmate","missing_stat")));
 }
 @Test void distanceTotalsUseRegisteredMovementStatsAndLongArithmetic(){
  var stats=new StatHandler();for(var id:MissionStatistics.walking())stats.setStat(null,Stats.CUSTOM.getOrCreateStat(id),Integer.MAX_VALUE);
  assertEquals(3L*Integer.MAX_VALUE,MissionStatistics.centimeters(stats,MissionStatistics.walking()));
 }
}
