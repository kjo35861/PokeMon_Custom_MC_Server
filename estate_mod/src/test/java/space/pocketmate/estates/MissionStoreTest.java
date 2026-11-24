package space.pocketmate.estates;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.time.*;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class MissionStoreTest {
 @TempDir Path root;
 static class Time extends Clock {
  Instant now=Instant.parse("2026-11-24T20:59:59Z");
  public ZoneId getZone(){return ZoneOffset.UTC;}public Clock withZone(ZoneId z){return this;}public Instant instant(){return now;}
 }
 Time time=new Time();UUID user=UUID.randomUUID(),other=UUID.randomUUID();
 Path file(){return root.resolve("missions.json");}
 MissionStore store() throws Exception{return new MissionStore(file(),time,false);}
 void finish(MissionStore s) throws Exception {
  for(var t:s.view(user).tasks()){
   if(t.metric().endsWith("_species"))for(int i=0;i<t.target();i++)s.event(user,Map.of(t.metric(),1),"species-"+i,"event-"+t.id()+i);
   else s.event(user,Map.of(t.metric(),t.target()),null,null);
  }
 }
 @Test void manyDaysNeverRepeatSlotsAndVariationStaysPractical() throws Exception {
  var s=store();s.view(user);
  var saved=com.google.gson.JsonParser.parseString(Files.readString(file())).getAsJsonObject();saved.addProperty("salt","unit-test-seed");Files.writeString(file(),saved.toString());s=store();
  Set<String> selected=new HashSet<>();
  for(int day=0;day<12;day++){
   time.now=Instant.parse("2026-11-25T00:00:00Z").plusSeconds(86400L*day);
   for(int player=0;player<8;player++){
    var tasks=s.view(new UUID(0,player)).tasks();assertEquals(5,tasks.stream().map(MissionStore.Task::id).distinct().count());
    for(int slot=0;slot<5;slot++){var t=tasks.get(slot);assertEquals(slot,t.slot());selected.add(t.id());}
   }
  }
  assertTrue(selected.containsAll(Set.of("lumber","miner","stone","sand","wild","battle","study","capture","encounters","harvest","plant","planks","food","fish","walk","roam")));
 }
 @Test void pixelmonSignalContractRejectsSummonsUnknownAndPvp() throws Exception {
  var s=store();var before=s.view(user);UUID poke=UUID.randomUUID(),battle=UUID.randomUUID();
  var natural=new PixelmonMissionSignals.Encounter(true,PixelmonMissionSignals.Origin.NATURAL);
  for(var origin:PixelmonMissionSignals.Origin.values())if(origin!=PixelmonMissionSignals.Origin.NATURAL){
   var summoned=new PixelmonMissionSignals.Encounter(true,origin);
   PixelmonMissionSignals.captured(s,user,poke,"rattata",summoned,time.instant());
   PixelmonMissionSignals.defeated(s,user,battle,poke,"rattata",summoned,time.instant());
   PixelmonMissionSignals.wonBattle(s,user,battle,List.of(summoned),false,false,time.instant());
  }
  var owned=new PixelmonMissionSignals.Encounter(false,PixelmonMissionSignals.Origin.NATURAL);
  PixelmonMissionSignals.defeated(s,user,battle,poke,"rattata",owned,time.instant());
  PixelmonMissionSignals.wonBattle(s,user,battle,List.of(natural),true,false,time.instant());
  PixelmonMissionSignals.wonBattle(s,user,battle,List.of(natural),false,true,time.instant());assertEquals(before,s.view(user));
  PixelmonMissionSignals.captured(s,user,poke,"rattata",natural,time.instant());assertEquals(1,s.view(user).tasks().get(2).progress());
  var first=s.view(user);PixelmonMissionSignals.captured(s,user,poke,"rattata",natural,time.instant());assertEquals(first,s.view(user));
  PixelmonMissionSignals.defeated(s,user,battle,poke,"rattata",natural,time.instant());PixelmonMissionSignals.wonBattle(s,user,battle,List.of(natural),false,false,time.instant());
  assertEquals(1,s.view(user).tasks().get(1).progress());
  var finished=s.view(user);PixelmonMissionSignals.defeated(s,user,UUID.randomUUID(),poke,"rattata",natural,time.instant());PixelmonMissionSignals.wonBattle(s,user,battle,List.of(natural),false,false,time.instant());assertEquals(finished,s.view(user));
  assertThrows(IllegalArgumentException.class,()->PixelmonMissionSignals.captured(s,user,poke,"Bad nickname!",natural,time.instant()));
 }
 @Test void rerollOncePersistsAcrossRestartAndKeepsOtherSlotsAndProgress() throws Exception {
  var s=store();var before=s.view(user);var chosen=before.tasks().getFirst();
  s.event(user,Map.of(chosen.metric(),1),null,null);var snapshot=s.view(user);
  time.now=time.now.plusMillis(1);
  assertTrue(s.reroll(user,snapshot.date(),chosen.id()));var after=s.view(user);
  assertEquals(0,after.rerollsRemaining());assertNotEquals(chosen.id(),after.tasks().getFirst().id());assertEquals(0,after.tasks().getFirst().progress());
  for(int i=1;i<5;i++)assertEquals(snapshot.tasks().get(i),after.tasks().get(i));
  assertEquals(5,after.tasks().stream().map(MissionStore.Task::metric).distinct().count());assertEquals(after,store().view(user));
  assertFalse(store().reroll(user,after.date(),after.tasks().get(1).id()));
  s.event(user,Map.of(after.tasks().getFirst().metric(),1),null,null);assertEquals(0,s.view(user).rerollsRemaining());
 }
 @Test void rerollRejectsInvalidCompleteClaimedOrOldDateWithoutSpending() throws Exception {
  var s=store();var before=s.view(user);
  assertFalse(s.reroll(user,"2000-01-01",before.tasks().getFirst().id()));assertFalse(s.reroll(user,before.date(),"unknown"));assertEquals(before,s.view(user));
  var task=before.tasks().getFirst();s.event(user,Map.of(task.metric(),task.target()),null,null);
  assertFalse(s.reroll(user,before.date(),task.id()));assertTrue(s.claim(user,task.id()));assertFalse(s.reroll(user,before.date(),task.id()));assertEquals(1,s.view(user).rerollsRemaining());
 }
 @Test void freeRerollRenewsOnlyAtSixAndNeverOnRestart() throws Exception {
  var s=store();var v=s.view(user);assertTrue(s.reroll(user,v.date(),v.tasks().getFirst().id()));assertEquals(0,store().view(user).rerollsRemaining());
  time.now=time.now.plusSeconds(1);assertEquals(1,store().view(user).rerollsRemaining());
 }
 @Test void eventsBeforeAssignmentOrBeforeReplacementNeverCount() throws Exception {
  var s=store();s.event(user,Map.of("logs",99,"stone",99,"ore",99,"sand",99),null,null);
  assertTrue(s.view(user).tasks().stream().allMatch(t->t.progress()==0));
  var before=s.view(user);Instant old=time.instant();time.now=time.now.plusMillis(1);
  assertTrue(s.reroll(user,before.date(),before.tasks().getFirst().id()));var current=s.view(user).tasks().getFirst();
  s.eventAt(user,Map.of(current.metric(),current.target()),null,"late-old-event",old);assertEquals(0,s.view(user).tasks().getFirst().progress());
  s.eventAt(user,Map.of(current.metric(),1),null,"new-event",time.instant());assertEquals(1,s.view(user).tasks().getFirst().progress());
 }
 @Test void failedRerollWriteKeepsQuotaAndAssignment() throws Exception {
  var s=store();var before=s.view(user);Files.delete(file());Files.createDirectory(file());Files.writeString(file().resolve("blocker"),"x");
  assertThrows(java.io.IOException.class,()->s.reroll(user,before.date(),before.tasks().getFirst().id()));assertEquals(before,s.view(user));
 }
 @Test void v1UpgradePreservesProgressClaimsAssignmentAndPlacedGuard() throws Exception {
  var s=store();var before=s.view(user);var t=before.tasks().getFirst();s.event(user,Map.of(t.metric(),t.target()),null,null);assertTrue(s.claim(user,t.id()));s.placed("world:123");
  var expected=s.view(user);var json=com.google.gson.JsonParser.parseString(Files.readString(file())).getAsJsonObject();json.addProperty("formatVersion",1);
  for(var entry:json.getAsJsonObject("days").entrySet()){var d=entry.getValue().getAsJsonObject();d.remove("rerollsUsed");d.remove("issuedTypes");for(var item:d.getAsJsonArray("tasks"))item.getAsJsonObject().remove("assignedAt");}
  Files.writeString(file(),json.toString());var upgraded=store();assertEquals(expected,upgraded.view(user));assertEquals(1,upgraded.receiptCount());assertTrue(upgraded.removePlaced("world:123"));
  assertEquals(2,com.google.gson.JsonParser.parseString(Files.readString(file())).getAsJsonObject().get("formatVersion").getAsInt());
 }
 @Test void movedPlacedBlocksStayProtectedAcrossPistonChainsAndRestarts() throws Exception {
  var s=store();s.placed("world:1");s.movePlaced(Map.of("world:1","world:2","world:2","world:3"));
  var next=store();assertFalse(next.removePlaced("world:1"));assertFalse(next.removePlaced("world:3"));assertTrue(next.removePlaced("world:2"));
 }
 @Test void fiveSlotsAreStableAndTargetsStayWithinBounds() throws Exception {
  var s=store();var a=s.view(user);assertEquals(5,a.tasks().size());assertEquals(a,s.view(user));assertEquals(a,store().view(user));
  for(int slot=0;slot<5;slot++){var t=a.tasks().get(slot);assertEquals(slot,t.slot());assertFalse(t.claimed());assertEquals(0,t.progress());
   var template=MissionStore.POOL.stream().filter(x->x.id().equals(t.id())).findFirst().orElseThrow();assertTrue(t.target()>=template.min()&&t.target()<=template.max());
  }
  assertFalse(Set.of("level","xp").contains(a.tasks().get(4).metric()));assertFalse(a.rewardsConfigured());
 }
 @Test void resetsAtKoreanSixIncludingOfflineRestart() throws Exception {
  var s=store();finish(s);assertTrue(s.claim(user,"final"));
  assertEquals("2026-11-24",s.view(user).date());assertEquals(Instant.parse("2026-11-24T21:00:00Z").toEpochMilli(),s.view(user).resetAt());
  time.now=time.now.plusSeconds(1);var next=store().view(user);assertEquals("2026-11-25",next.date());assertFalse(next.finalClaimed());assertTrue(next.tasks().stream().allMatch(t->t.progress()==0&&!t.claimed()));assertEquals(1,store().receiptCount());
 }
 @Test void midnightDoesNotResetAndMonthBoundaryIsCorrect(){
  assertEquals(LocalDate.of(2026,11,24),MissionStore.dayAt(Instant.parse("2026-11-24T15:00:00Z")));
  assertEquals(LocalDate.of(2026,11,30),MissionStore.dayAt(Instant.parse("2026-11-30T20:59:59Z")));
  assertEquals(LocalDate.of(2026,12,1),MissionStore.dayAt(Instant.parse("2026-11-30T21:00:00Z")));
 }
 @Test void noEarlyDuplicateOrUnknownClaimsAndFinalNeedsFive() throws Exception {
  var s=store();assertFalse(s.claim(user,"final"));assertFalse(s.claim(user,"unknown"));
  var first=s.view(user).tasks().getFirst();assertFalse(s.claim(user,first.id()));
  s.event(user,Map.of(first.metric(),Integer.MAX_VALUE),null,null);assertTrue(s.claim(user,first.id()));assertFalse(s.claim(user,first.id()));assertFalse(s.claim(user,"final"));assertEquals(1,s.receiptCount());
  finish(s);assertTrue(s.claim(user,"final"));assertFalse(s.claim(user,"final"));assertTrue(store().view(user).finalClaimed());
 }
 @Test void speciesAndEventKeysDeduplicateAndOtherPlayersAreIsolated() throws Exception {
  var s=store();s.view(user);var before=s.view(other);
  var amounts=Map.of("capture",1,"capture_species",1,"defeat",1,"defeat_species",1,"battle_win",1);
  s.event(user,amounts,"rattata","same-event");var first=s.view(user);s.event(user,amounts,"rattata","same-event");assertEquals(first,s.view(user));
  s.event(user,Map.of("capture_species",1,"defeat_species",1),"rattata","different-event");assertEquals(first,s.view(user));assertEquals(before,s.view(other));
 }
 @Test void incorrectAndNegativeMetricsNeverAdvance() throws Exception {
  var s=store();var before=s.view(user);s.event(user,Map.of("unknown",999,"logs",-12),null,null);assertEquals(before,s.view(user));
 }
 @Test void placedGuardSurvivesRestartAndCannotBeConsumedTwice() throws Exception {
  var s=store();s.placed("minecraft:overworld:123");var next=store();assertTrue(next.removePlaced("minecraft:overworld:123"));assertFalse(next.removePlaced("minecraft:overworld:123"));assertFalse(store().removePlaced("minecraft:overworld:123"));
 }
 @Test void badStoreFailsClosedInsteadOfResetting() throws Exception {
  Files.writeString(file(),"{not valid");assertThrows(java.io.IOException.class,()->store());
 }
 @Test void rewardsPersistAcrossAllClaimsAndNewDay() throws Exception {
  var s=store();finish(s);for(var t:s.view(user).tasks())assertTrue(s.claim(user,t.id()));assertTrue(s.claim(user,"final"));assertEquals(6,store().receiptCount());
  time.now=time.now.plusSeconds(2);assertTrue(store().view(user).tasks().stream().allMatch(t->!t.claimed()));assertEquals(6,store().receiptCount());
 }
 @Test void failedClaimWriteDoesNotAcknowledgeOrChangeMemory() throws Exception {
  var s=store();finish(s);Files.delete(file());Files.createDirectory(file());Files.writeString(file().resolve("blocker"),"x");
  assertThrows(java.io.IOException.class,()->s.claim(user,"final"));assertFalse(s.view(user).finalClaimed());assertEquals(0,s.receiptCount());
 }
}
