package space.pocketmate.estates;

import com.google.gson.*;
import java.io.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;

/** Server-owned daily assignments. No currency or inventory is modified until rewards are configured. */
public final class MissionStore {
    public static final ZoneId ZONE=ZoneId.of("Asia/Seoul");
    private static final Gson JSON=new GsonBuilder().setPrettyPrinting().create();
    public record Template(String id,int slot,String name,String description,String metric,int min,int max,boolean pokemon) {}
    public record Task(String id,int slot,String name,String description,String metric,int target,int progress,boolean claimed,Set<String> seen,long assignedAt) {
        public Task { seen=Set.copyOf(seen); }
        public boolean complete(){return progress>=target;}
    }
    public record Day(String date,List<Task> tasks,boolean finalClaimed,Set<String> events,int rerollsUsed,Set<String> issuedTypes) {
        public Day {tasks=List.copyOf(tasks);events=Set.copyOf(events);issuedTypes=Set.copyOf(issuedTypes);}
    }
    private static Day updated(Day day,List<Task> tasks,boolean finalClaimed,Set<String> events){return new Day(day.date,tasks,finalClaimed,events,day.rerollsUsed,day.issuedTypes);}
    public record View(String date,long resetAt,List<Task> tasks,boolean finalClaimed,boolean rewardsConfigured,int rerollsRemaining) {}
    public static final List<Template> POOL=List.of(
        new Template("lumber",0,"숲속의 나무꾼","원목 %d개 채집하기","logs",32,48,false),
        new Template("miner",0,"광산의 일꾼","종류에 상관없이 광석 %d개 채굴하기","ore",8,12,false),
        new Template("stone",0,"돌을 캐는 하루","돌·심층암·화강암·섬록암·안산암 %d개 채굴하기","stone",48,64,false),
        new Template("sand",0,"모래 위의 발자국","모래 또는 붉은 모래 %d개 채집하기","sand",24,40,false),
        new Template("wild",1,"야생의 도전자","야생 포켓몬 %d마리 처치하기","defeat",5,7,true),
        new Template("battle",1,"실전 훈련","야생 포켓몬 배틀 %d회 승리하기","battle_win",4,6,true),
        new Template("study",1,"종족 연구","서로 다른 종류의 야생 포켓몬 %d종 처치하기","defeat_species",3,4,true),
        new Template("capture",2,"새로운 동료","야생 포켓몬 %d마리 포획하기","capture",2,3,true),
        new Template("encounters",2,"다양한 만남","서로 다른 종류의 야생 포켓몬 %d종 포획하기","capture_species",2,2,true),
        new Template("harvest",3,"풍요로운 수확","완전히 자란 작물 %d칸 수확하기","harvest",16,24,false),
        new Template("plant",3,"씨앗을 심는 사람","작물 %d칸 심기","plant",16,24,false),
        new Template("planks",3,"목재 가공 전문가","종류에 상관없이 나무판자 %d개 제작하기","planks",32,48,false),
        new Template("food",3,"초보 요리사","제작대 또는 인벤토리에서 음식 %d개 제작하기","food",6,10,false),
        new Template("fish",3,"여유로운 낚시꾼","낚시로 물고기 %d마리 낚기","fish",3,4,false),
        new Template("walk",4,"모험의 시작","도보로 %d블록 이동하기","walk",500,800,false),
        new Template("roam",4,"세계의 방랑자","도보·수영·탑승으로 총 %d블록 이동하기","travel",800,1200,false),
        new Template("level",4,"성장하는 파트너","포켓몬 레벨 총 %d 올리기","level",2,3,true),
        new Template("xp",4,"꾸준한 훈련","포켓몬 경험치 %d 획득하기","xp",300,500,true)
    );
    private final Path file;
    private final Clock clock;
    private final boolean training;
    private String salt=UUID.randomUUID().toString();
    private Map<UUID,Day> days=new HashMap<>();
    private Set<String> placed=new HashSet<>();
    private Map<String,Long> receipts=new HashMap<>();
    public MissionStore(Path file,Clock clock,boolean training) throws IOException {
        this.file=file;this.clock=clock;this.training=training;
        if(!Files.exists(file))return;
        try {
            JsonObject data=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
            int version=data.get("formatVersion").getAsInt();if(version!=1&&version!=2)throw new IllegalArgumentException();
            salt=data.get("salt").getAsString();
            if(data.has("receipts"))for(var e:data.getAsJsonObject("receipts").entrySet())receipts.put(e.getKey(),e.getValue().getAsLong());
            for(var p:data.getAsJsonArray("placed"))placed.add(p.getAsString());
            for(var entry:data.getAsJsonObject("days").entrySet()){
                JsonObject stored=entry.getValue().getAsJsonObject().deepCopy();
                if(version==1){
                    stored.addProperty("rerollsUsed",0);Set<String> types=new HashSet<>();
                    for(var item:stored.getAsJsonArray("tasks")){var t=item.getAsJsonObject();types.add(t.get("metric").getAsString());t.addProperty("assignedAt",clock.millis());}
                    stored.add("issuedTypes",JSON.toJsonTree(types));
                }
                Day day=JSON.fromJson(stored,Day.class);
                if(day.tasks.size()!=5||day.date==null||day.rerollsUsed<0||day.rerollsUsed>1)throw new IllegalArgumentException();
                for(int i=0;i<5;i++){Task t=day.tasks.get(i);if(t.slot!=i||t.target<1||t.progress<0||t.progress>t.target||t.assignedAt<0)throw new IllegalArgumentException();}
                if(day.tasks.stream().map(Task::metric).distinct().count()!=5||!day.issuedTypes.containsAll(day.tasks.stream().map(Task::metric).toList()))throw new IllegalArgumentException();
                days.put(UUID.fromString(entry.getKey()),day);
            }
            if(version==1)write(days,placed);
        }catch(Exception invalid){throw new IOException("Invalid mission store; refusing to reset progress or claims",invalid);}
    }
    public static LocalDate dayAt(Instant now){return now.atZone(ZONE).minusHours(6).toLocalDate();}
    public static long nextReset(Instant now){return dayAt(now).plusDays(1).atTime(6,0).atZone(ZONE).toInstant().toEpochMilli();}
    private Day assignments(UUID player){
        String date=dayAt(clock.instant()).toString();
        var random=new SplittableRandom(Objects.hash(salt,player,date));List<Task> tasks=new ArrayList<>();
        for(int slot=0;slot<5;slot++){
            final int index=slot;
            List<Template> pool=POOL.stream().filter(t->t.slot==index&&(index!=4||training||!t.pokemon)).toList();
            Template t=pool.get(random.nextInt(pool.size()));int target=random.nextInt(t.min,t.max+1);
            tasks.add(new Task(t.id,slot,t.name,t.description.formatted(target),t.metric,target,0,false,Set.of(),clock.millis()));
        }
        return new Day(date,tasks,false,Set.of(),0,new HashSet<>(tasks.stream().map(Task::metric).toList()));
    }
    private Day day(UUID player) throws IOException {
        Day current=days.get(player);
        if(current==null||!current.date.equals(dayAt(clock.instant()).toString())){
            current=assignments(player);save(player,current,placed);
        }
        return current;
    }
    public View view(UUID player) throws IOException {Day d=day(player);return new View(d.date,nextReset(clock.instant()),d.tasks,d.finalClaimed,false,1-d.rerollsUsed);}
    /** Only trusted server event adapters call this. Unique keys deduplicate completed battle/capture events. */
    public void event(UUID player,Map<String,Integer> amounts,String species,String unique) throws IOException {
        eventAt(player,amounts,species,unique,clock.instant());
    }
    public void eventAt(UUID player,Map<String,Integer> amounts,String species,String unique,Instant occurredAt) throws IOException {
        Day d=days.get(player);
        if(occurredAt==null||d==null||!d.date.equals(dayAt(clock.instant()).toString())||occurredAt.isAfter(clock.instant())||!d.date.equals(dayAt(occurredAt).toString()))return;
        if(unique!=null&&d.events.contains(unique))return;
        List<Task> tasks=new ArrayList<>();boolean changed=false;
        for(Task t:d.tasks){
            int n=Math.max(0,amounts.getOrDefault(t.metric,0));Set<String> seen=new HashSet<>(t.seen);int progress=t.progress;
            if(n>0&&!t.complete()&&occurredAt.toEpochMilli()>=t.assignedAt){
                if(t.metric.endsWith("_species"))n=species!=null&&seen.add(species)?1:0;
                progress=(int)Math.min(t.target,(long)progress+n);
            }
            changed|=progress!=t.progress;
            tasks.add(new Task(t.id,t.slot,t.name,t.description,t.metric,t.target,progress,t.claimed,seen,t.assignedAt));
        }
        if(changed||unique!=null){Set<String> events=new HashSet<>(d.events);if(unique!=null)events.add(unique);save(player,updated(d,tasks,d.finalClaimed,events),placed);}
    }
    public boolean claim(UUID player,String taskId) throws IOException {
        Day d=day(player);List<Task> tasks=new ArrayList<>(d.tasks);
        if(taskId.equals("final")){
            if(d.finalClaimed||d.tasks.stream().anyMatch(t->!t.complete()))return false;
            saveClaim(player,updated(d,tasks,true,d.events),"final");return true;
        }
        for(int i=0;i<tasks.size();i++){
            Task t=tasks.get(i);if(!t.id.equals(taskId))continue;
            if(!t.complete()||t.claimed)return false;
            tasks.set(i,new Task(t.id,t.slot,t.name,t.description,t.metric,t.target,t.progress,true,t.seen,t.assignedAt));
            saveClaim(player,updated(d,tasks,d.finalClaimed,d.events),taskId);return true;
        }
        return false;
    }
    /** One free replacement per player per reset day. Other slots and claim receipts remain untouched. */
    public boolean reroll(UUID player,String date,String taskId) throws IOException {
        Day d=day(player);if(!d.date.equals(date)||d.rerollsUsed>=1||d.finalClaimed)return false;
        List<Task> tasks=new ArrayList<>(d.tasks);
        for(int i=0;i<tasks.size();i++){
            Task old=tasks.get(i);if(!old.id.equals(taskId))continue;
            if(old.complete()||old.claimed)return false;
            List<Template> pool=POOL.stream().filter(t->t.slot==old.slot&&(t.slot!=4||training||!t.pokemon)&&!d.issuedTypes.contains(t.metric)).toList();
            if(pool.isEmpty())return false;
            var random=new SplittableRandom(Objects.hash(salt,player,date,"reroll",taskId));Template t=pool.get(random.nextInt(pool.size()));int target=random.nextInt(t.min,t.max+1);
            tasks.set(i,new Task(t.id,t.slot,t.name,t.description.formatted(target),t.metric,target,0,false,Set.of(),clock.millis()));
            Set<String> issued=new HashSet<>(d.issuedTypes);issued.add(t.metric);
            save(player,new Day(d.date,tasks,d.finalClaimed,d.events,1,issued),placed);return true;
        }
        return false;
    }
    private void saveClaim(UUID player,Day day,String task) throws IOException {
        String key=player+":"+day.date+":"+task;
        if(receipts.containsKey(key))throw new IOException("Duplicate reward receipt; refusing inconsistent claim");
        Map<UUID,Day> next=new HashMap<>(days);next.put(player,day);
        Map<String,Long> nextReceipts=new HashMap<>(receipts);nextReceipts.put(key,clock.millis());
        write(next,placed,nextReceipts);days=next;receipts=nextReceipts;
    }
    public int receiptCount(){return receipts.size();}
    public void placed(String position) throws IOException {if(!placed.contains(position)){Set<String> next=new HashSet<>(placed);next.add(position);write(days,next);placed=next;}}
    public void movePlaced(Map<String,String> moves) throws IOException {
        Set<String> tracked=new HashSet<>();for(String source:moves.keySet())if(placed.contains(source))tracked.add(source);
        if(tracked.isEmpty())return;
        Set<String> next=new HashSet<>(placed);next.removeAll(moves.keySet());for(String source:tracked)next.add(moves.get(source));
        write(days,next);placed=next;
    }
    public boolean removePlaced(String position) throws IOException {
        if(!placed.contains(position))return false;
        Set<String> next=new HashSet<>(placed);next.remove(position);write(days,next);placed=next;return true;
    }
    private void save(UUID player,Day day,Set<String> positions) throws IOException {Map<UUID,Day> next=new HashMap<>(days);next.put(player,day);write(next,positions);days=next;}
    private void write(Map<UUID,Day> next,Set<String> positions) throws IOException {write(next,positions,receipts);}
    private void write(Map<UUID,Day> next,Set<String> positions,Map<String,Long> nextReceipts) throws IOException {
        JsonObject data=new JsonObject();data.addProperty("formatVersion",2);data.addProperty("salt",salt);data.add("days",JSON.toJsonTree(next));data.add("placed",JSON.toJsonTree(positions));data.add("receipts",JSON.toJsonTree(nextReceipts));
        Files.createDirectories(file.getParent());Path temp=Files.createTempFile(file.getParent(),"missions-",".tmp");
        try{
            byte[] bytes=JSON.toJson(data).getBytes(java.nio.charset.StandardCharsets.UTF_8);
            try(var ch=java.nio.channels.FileChannel.open(temp,StandardOpenOption.WRITE)){var buf=java.nio.ByteBuffer.wrap(bytes);while(buf.hasRemaining())ch.write(buf);ch.force(true);}
            if(Files.exists(file)&&!Files.isRegularFile(file))throw new IOException("Mission data target is not a regular file");
            if(Files.exists(file))Files.copy(file,file.resolveSibling(file.getFileName()+".bak"),StandardCopyOption.REPLACE_EXISTING);
            try{Files.move(temp,file,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}catch(AtomicMoveNotSupportedException ignored){Files.move(temp,file,StandardCopyOption.REPLACE_EXISTING);}
        }finally{Files.deleteIfExists(temp);}
    }
}
