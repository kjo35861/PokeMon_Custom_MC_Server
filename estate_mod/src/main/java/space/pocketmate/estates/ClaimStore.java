package space.pocketmate.estates;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonElement;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** One store per saved world. No browser-provided ownership or identity is ever accepted. */
public final class ClaimStore {
    public record Key(int x, int z) {}
    public record Claim(int x, int z, UUID owner, String ownerName, long createdAt) {}
    public enum Role { LORD, STEWARD, RESIDENT }
    public record Member(UUID id,String name,Role role,long joinedAt) {}
    public record Invitation(UUID id,String name,long at) {}
    public record KnownPlayer(UUID id,String name,long lastSeen) {}
    public record Home(double x,double y,double z,float yaw,float pitch,boolean surface) {}
    public record Estate(UUID owner,String name,List<Member> members,List<Invitation> invitations,String announcement,String image,Home home) {
        public Estate { members=List.copyOf(members);invitations=List.copyOf(invitations); }
    }
    public static final class Denied extends Exception { Denied(String message){super(message);} }
    public record Wallet(UUID owner,long balance) {}
    private final Map<UUID,Long> balances=new LinkedHashMap<>();
    public record VaultEntry(String type,long amount,int level,UUID actor,long at) {}
    public record Progress(UUID owner,int level,long treasury,int purchasedChunks,List<VaultEntry> ledger) {
        public Progress { ledger=List.copyOf(ledger); }
    }
    private final Map<UUID,Progress> progress=new LinkedHashMap<>();
    private final Map<UUID,Estate> estates=new LinkedHashMap<>();
    private final Map<UUID,KnownPlayer> players=new LinkedHashMap<>();
    private static final class State {
        int formatVersion = 4;
        String dimension = "minecraft:overworld";
        List<Claim> claims = new ArrayList<>();
        List<Estate> estates = new ArrayList<>();
        List<KnownPlayer> players = new ArrayList<>();
        List<Progress> progress = new ArrayList<>();
        List<Wallet> balances = new ArrayList<>();
    }
    public enum Failure { OCCUPIED, ALREADY_HAS_ESTATE, NO_ESTATE, NOT_ADJACENT, OUT_OF_BOUNDS, INVALID_SELECTION, CHUNK_LIMIT }
    public static final class Rejected extends Exception {
        public final Failure reason;
        Rejected(Failure reason) { super(reason.name()); this.reason = reason; }
    }
    private final Path path;
    private final Map<Key,Claim> claims = new LinkedHashMap<>();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    public ClaimStore(Path path) throws IOException {
        this.path = path;
        if (!Files.exists(path)) return;
        try {
            JsonObject document=JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            // Required fields must be present; Gson field defaults must never turn a damaged file into an empty store.
            if(!document.has("formatVersion")||!document.has("dimension")||!document.has("claims")||!document.get("claims").isJsonArray())
                throw new IOException("Missing estate ownership metadata");
            for(JsonElement entry:document.getAsJsonArray("claims")) {
                JsonObject value=entry.getAsJsonObject();
                for(String field:List.of("x","z","owner","ownerName","createdAt"))
                    if(!value.has(field)||value.get(field).isJsonNull())throw new IOException("Incomplete chunk ownership");
                for(String field:List.of("x","z","createdAt")) {
                    if(!value.get(field).isJsonPrimitive()||!value.getAsJsonPrimitive(field).isNumber())throw new IOException("Invalid ownership coordinates");
                    double number=value.get(field).getAsDouble();
                    if(!Double.isFinite(number)||number!=Math.rint(number))throw new IOException("Invalid ownership coordinates");
                    if(!field.equals("createdAt")&&(number<Integer.MIN_VALUE||number>Integer.MAX_VALUE))throw new IOException("Invalid ownership coordinates");
                }
            }
            if(document.get("formatVersion").getAsInt()==4)for(JsonElement entry:document.getAsJsonArray("estates")){
                JsonObject home=entry.getAsJsonObject().getAsJsonObject("home");
                if(home==null)throw new IOException("Missing estate home");
                for(String field:List.of("x","y","z","yaw","pitch","surface")){
                    JsonElement value=home.get(field);
                    if(value==null||!value.isJsonPrimitive()||(field.equals("surface")?!value.getAsJsonPrimitive().isBoolean():!value.getAsJsonPrimitive().isNumber()))throw new IOException("Incomplete estate home");
                }
            }
            State state = GSON.fromJson(document, State.class);
            if (state == null || (state.formatVersion != 1 && state.formatVersion != 2 && state.formatVersion != 3 && state.formatVersion != 4) || !"minecraft:overworld".equals(state.dimension) || state.claims == null)
                throw new IOException("Invalid estate ownership file");
            for (Claim claim : state.claims) {
                if (claim == null || claim.owner == null || claim.ownerName == null || claim.ownerName.isBlank() || claim.createdAt < 0 || !inBounds(claim.x,claim.z) ||
                    claims.putIfAbsent(new Key(claim.x,claim.z),claim) != null) throw new IOException("Invalid or duplicate chunk ownership");
            }
            if(state.formatVersion==1){
                for(Claim claim:claims.values())estates.computeIfAbsent(claim.owner,id->new Estate(id,claim.ownerName+"의 영지",List.of(new Member(id,claim.ownerName,Role.LORD,claim.createdAt)),List.of(),"","",null));
            }else{
                if(!document.has("estates")||!document.get("estates").isJsonArray()||!document.has("players")||!document.get("players").isJsonArray())throw new IOException("Missing estate community data");
                Set<UUID> members=new HashSet<>();
                for(Estate estate:state.estates){
                    if(estate.owner==null||estate.name==null||estate.name.isBlank()||estate.name.length()>80||estate.announcement==null||estate.announcement.length()>1000||estate.image==null||estate.image.length()>18000||estate.members.isEmpty()||estate.members.size()>64||estate.invitations.size()>64||estates.putIfAbsent(estate.owner,estate)!=null)throw new IOException("Invalid estate community");
                    long lords=0;for(Member member:estate.members){
                        if(member.id==null||member.name==null||member.name.isBlank()||member.role==null||member.joinedAt<0||!members.add(member.id))throw new IOException("Invalid estate member");
                        if(member.role==Role.LORD){if(!member.id.equals(estate.owner))throw new IOException("Invalid lord");lords++;}
                    }
                    if(lords!=1)throw new IOException("Missing lord");
                    Set<UUID> invited=new HashSet<>();for(Invitation invite:estate.invitations)if(invite.id==null||invite.name==null||invite.name.isBlank()||invite.at<0||!invited.add(invite.id))throw new IOException("Invalid invitation");
                }
                for(KnownPlayer player:state.players)if(player.id==null||player.name==null||player.name.isBlank()||player.lastSeen<0||players.putIfAbsent(player.id,player)!=null)throw new IOException("Invalid player history");
                for(Claim claim:claims.values())if(!estates.containsKey(claim.owner))throw new IOException("Ownership has no estate");
                for(Estate estate:estates.values())if(owned(estate.owner).isEmpty())throw new IOException("Estate has no ownership");
            }
            for(Estate estate:new ArrayList<>(estates.values())){
                if(state.formatVersion<4){
                    Claim first=owned(estate.owner).stream().min(Comparator.comparingLong(Claim::createdAt)).orElseThrow();
                    estates.put(estate.owner,new Estate(estate.owner,estate.name,estate.members,estate.invitations,estate.announcement,estate.image,new Home(first.x*16+8.5,0,first.z*16+8.5,0,0,true)));
                }else if(!validHome(estate.home)||get(homeChunk(estate.home.x),homeChunk(estate.home.z))==null||!get(homeChunk(estate.home.x),homeChunk(estate.home.z)).owner.equals(estate.owner))throw new IOException("Invalid estate home");
            }
            if(state.formatVersion<3){
                for(Estate estate:estates.values()){int count=owned(estate.owner).size();progress.put(estate.owner,new Progress(estate.owner,EstateRules.migrationLevel(count),0,count,List.of()));}
            }else{
                if(!document.has("progress")||!document.get("progress").isJsonArray())throw new IOException("Missing estate progression");
                for(JsonElement element:document.getAsJsonArray("progress")){
                    JsonObject value=element.getAsJsonObject();
                    for(String field:List.of("level","treasury","purchasedChunks")){
                        JsonElement number=value.get(field);if(number==null||!number.isJsonPrimitive()||!number.getAsJsonPrimitive().isNumber())throw new IOException("Invalid estate progression number");
                        try{long n=number.getAsBigDecimal().toBigIntegerExact().longValueExact();long max=field.equals("level")?10:field.equals("purchasedChunks")?1_000_000:EstateRules.MAX_MONEY;if(n<0||n>max)throw new ArithmeticException();}catch(ArithmeticException invalid){throw new IOException("Invalid estate progression number",invalid);}
                    }
                }
                for(Progress value:state.progress){
                    if(value.owner==null||!estates.containsKey(value.owner)||value.level<0||value.level>EstateRules.MAX_LEVEL||value.treasury<0||value.treasury>EstateRules.MAX_MONEY||value.purchasedChunks<owned(value.owner).size()||value.purchasedChunks>1_000_000||value.ledger.size()>50||progress.putIfAbsent(value.owner,value)!=null)throw new IOException("Invalid estate progression");
                    for(VaultEntry entry:value.ledger)if(entry.type==null||!Set.of("TEST_CREDIT","UPGRADE","PURCHASE","DEPOSIT","AUTO_DEPOSIT").contains(entry.type)||entry.amount<0||entry.amount>EstateRules.MAX_MONEY||entry.level<0||entry.level>10||entry.actor==null||entry.at<0)throw new IOException("Invalid vault entry");
                }
                if(progress.size()!=estates.size())throw new IOException("Estate has no progression");
                if(!document.has("balances")||!document.get("balances").isJsonArray())throw new IOException("Missing wallet balances");
                for(JsonElement element:document.getAsJsonArray("balances")){
                    JsonElement number=element.getAsJsonObject().get("balance");if(number==null||!number.isJsonPrimitive()||!number.getAsJsonPrimitive().isNumber())throw new IOException("Invalid wallet balance");
                    try{number.getAsBigDecimal().toBigIntegerExact().longValueExact();}catch(ArithmeticException invalid){throw new IOException("Invalid wallet balance",invalid);}
                }
                for(Wallet wallet:state.balances)if(wallet.owner==null||wallet.balance<0||wallet.balance>EstateRules.MAX_MONEY||balances.putIfAbsent(wallet.owner,wallet.balance)!=null)throw new IOException("Invalid wallet balance");
            }
        } catch (RuntimeException error) { throw new IOException("Estate data could not be read; refusing to reset ownership",error); }
    }
    public static boolean inBounds(int x,int z) { return Math.abs((long)x) <= 1_874_998 && Math.abs((long)z) <= 1_874_998; }
    public synchronized Claim get(int x,int z) { return claims.get(new Key(x,z)); }
    public synchronized List<Claim> owned(UUID owner) { return claims.values().stream().filter(c->c.owner.equals(owner)).toList(); }
    public synchronized boolean adjacent(UUID owner,int x,int z) {
        for (Key key : List.of(new Key(x-1,z),new Key(x+1,z),new Key(x,z-1),new Key(x,z+1))) {
            Claim claim=claims.get(key);if(claim!=null && claim.owner.equals(owner))return true;
        }
        return false;
    }
    public synchronized Claim buy(UUID owner,String ownerName,int x,int z,boolean create) throws Rejected,IOException {
        if(!create)try{return buyBatch(owner,ownerName,List.of(new Key(x,z))).getFirst();}catch(Denied denied){throw new IOException(denied.getMessage(),denied);}
        try{return createEstate(owner,ownerName,ownerName+"의 영지",x,z);}catch(Denied denied){throw new Rejected(Failure.ALREADY_HAS_ESTATE);}
    }
    public synchronized Claim createEstate(UUID owner,String ownerName,String name,int x,int z) throws Rejected,IOException,Denied {
        return createEstate(owner,ownerName,name,x,z,new Home(x*16+8.5,0,z*16+8.5,0,0,true));
    }
    public synchronized Claim createEstate(UUID owner,String ownerName,String name,int x,int z,Home home) throws Rejected,IOException,Denied {
        name=validName(name);
        if(!inBounds(x,z))throw new Rejected(Failure.OUT_OF_BOUNDS);
        if(!validHome(home)||homeChunk(home.x)!=x||homeChunk(home.z)!=z)throw new Denied("영지 홈은 최초 영지 청크 안에 있어야 합니다.");
        if(estateFor(owner)!=null)throw new Denied("이미 소속된 영지가 있습니다.");
        boolean create=true;
        if (!inBounds(x,z))throw new Rejected(Failure.OUT_OF_BOUNDS);
        if (claims.containsKey(new Key(x,z))) throw new Rejected(Failure.OCCUPIED);
        boolean hasEstate=claims.values().stream().anyMatch(c->c.owner.equals(owner));
        if (create && hasEstate)throw new Rejected(Failure.ALREADY_HAS_ESTATE);
        if (!create && !hasEstate)throw new Rejected(Failure.NO_ESTATE);
        if (!create && !adjacent(owner,x,z))throw new Rejected(Failure.NOT_ADJACENT);
        Claim claim=new Claim(x,z,owner,ownerName,System.currentTimeMillis());
        Map<Key,Claim> next=new LinkedHashMap<>(claims);next.put(new Key(x,z),claim);
        // Commit durable ownership before announcing success. A failed save never updates memory.
        Map<UUID,Estate> nextEstates=new LinkedHashMap<>(estates);
        nextEstates.put(owner,new Estate(owner,name,List.of(new Member(owner,ownerName,Role.LORD,claim.createdAt)),List.of(),"","",home));
        Map<UUID,Progress> nextProgress=new LinkedHashMap<>(progress);nextProgress.put(owner,new Progress(owner,0,0,1,List.of()));
        persist(next.values(),nextEstates,players,nextProgress);progress.clear();progress.putAll(nextProgress);claims.put(new Key(x,z),claim);estates.clear();estates.putAll(nextEstates);return claim;
    }
    /** Validate the whole expansion, then commit once. Selected chunks may connect through one another. */
    public synchronized List<Claim> buyBatch(UUID owner,String ownerName,List<Key> selected) throws Rejected,IOException,Denied {
        if(selected==null||selected.isEmpty()||selected.size()>128)throw new Rejected(Failure.INVALID_SELECTION);
        Set<Key> remaining=new LinkedHashSet<>(selected);
        if(remaining.size()!=selected.size())throw new Rejected(Failure.INVALID_SELECTION);
        for(Key key:remaining){
            if(key==null||!inBounds(key.x,key.z))throw new Rejected(Failure.OUT_OF_BOUNDS);
            if(claims.containsKey(key))throw new Rejected(Failure.OCCUPIED);
        }
        if(owned(owner).isEmpty())throw new Rejected(Failure.NO_ESTATE);
        ArrayDeque<Key> connected=new ArrayDeque<>();
        for(Key key:remaining)if(adjacent(owner,key.x,key.z))connected.add(key);
        remaining.removeAll(connected);
        while(!connected.isEmpty()){
            Key key=connected.removeFirst();
            for(Key neighbor:List.of(new Key(key.x-1,key.z),new Key(key.x+1,key.z),new Key(key.x,key.z-1),new Key(key.x,key.z+1)))
                if(remaining.remove(neighbor))connected.addLast(neighbor);
        }
        if(!remaining.isEmpty())throw new Rejected(Failure.NOT_ADJACENT);
        Progress current=progress.get(owner);if(current==null)throw new Rejected(Failure.NO_ESTATE);
        if(owned(owner).size()+selected.size()>EstateRules.limit(current.level))throw new Rejected(Failure.CHUNK_LIMIT);
        long cost=EstateRules.purchasePrice(current.purchasedChunks,selected.size());
        long charged=cost,topUp=Math.max(0,charged-current.treasury);
        if(wallet(owner)<topUp)throw new Denied("영지 금고와 영주 개인 재화를 합쳐도 금액이 부족합니다. 전체 구매가 취소되었습니다.");
        Map<UUID,Long> nextBalances=new LinkedHashMap<>(balances);if(topUp>0)nextBalances.put(owner,wallet(owner)-topUp);
        List<VaultEntry> ledger=current.ledger;
        if(topUp>0)ledger=appendLedger(ledger,new VaultEntry("AUTO_DEPOSIT",topUp,current.level,owner,System.currentTimeMillis()));
        if(charged>0)ledger=appendLedger(ledger,new VaultEntry("PURCHASE",charged,current.level,owner,System.currentTimeMillis()));
        Progress updated=new Progress(owner,current.level,current.treasury+topUp-charged,Math.addExact(current.purchasedChunks,selected.size()),ledger);
        Map<UUID,Progress> nextProgress=new LinkedHashMap<>(progress);nextProgress.put(owner,updated);
        Map<Key,Claim> next=new LinkedHashMap<>(claims);List<Claim> purchased=new ArrayList<>();long now=System.currentTimeMillis();
        for(Key key:selected){Claim claim=new Claim(key.x,key.z,owner,ownerName,now);next.put(key,claim);purchased.add(claim);}
        persist(next.values(),estates,players,nextProgress,nextBalances);balances.clear();balances.putAll(nextBalances);progress.clear();progress.putAll(nextProgress);claims.clear();claims.putAll(next);return List.copyOf(purchased);
    }
    public static String validName(String value) throws Denied {
        if(value==null)throw new Denied("영지 이름을 입력해주세요.");String name=value.strip();
        if(name.isBlank()||name.codePointCount(0,name.length())>24||name.codePoints().anyMatch(c->Character.isISOControl(c)||c=='<'||c=='>'))throw new Denied("영지 이름은 1~24자로 입력해주세요. 줄바꿈과 꺾쇠는 사용할 수 없습니다.");
        return name;
    }
    public synchronized Estate estateFor(UUID player){return estates.values().stream().filter(e->e.members.stream().anyMatch(m->m.id.equals(player))).findFirst().orElse(null);}
    private static int homeChunk(double position){return (int)Math.floor(position/16);}
    private static boolean validHome(Home home){return home!=null&&Double.isFinite(home.x)&&Double.isFinite(home.y)&&Double.isFinite(home.z)&&Float.isFinite(home.yaw)&&Float.isFinite(home.pitch)&&home.y>=-64&&home.y<320&&home.pitch>=-90&&home.pitch<=90&&inBounds(homeChunk(home.x),homeChunk(home.z))&&Math.abs(home.x)<30_000_000&&Math.abs(home.z)<30_000_000;}
    public synchronized Home homeFor(UUID actor) throws Denied {
        Estate estate=estateFor(actor);if(estate==null)throw new Denied("소속된 영지가 없습니다. 먼저 영지를 생성하거나 초대를 수락해 주세요.");return estate.home;
    }
    public synchronized void setHome(UUID actor,Home home) throws Denied,IOException {
        Estate estate=lord(actor);
        if(!validHome(home)||home.surface)throw new Denied("홈 위치가 올바르지 않습니다.");
        Claim claim=get(homeChunk(home.x),homeChunk(home.z));
        if(claim==null||!claim.owner.equals(estate.owner))throw new Denied("내 영지 안에서만 홈 지점을 지정할 수 있습니다.");
        saveEstate(new Estate(estate.owner,estate.name,estate.members,estate.invitations,estate.announcement,estate.image,home));
    }
    public synchronized List<KnownPlayer> knownPlayers(){return List.copyOf(players.values());}
    public synchronized KnownPlayer known(UUID id){return players.get(id);}
    public synchronized List<Estate> invitationsFor(UUID id){long cutoff=System.currentTimeMillis()-7*86400000L;return estates.values().stream().filter(e->e.invitations.stream().anyMatch(i->i.id.equals(id)&&i.at>=cutoff)).limit(20).toList();}
    public synchronized void seen(UUID id,String name,long now) throws IOException {
        Map<UUID,KnownPlayer> next=new LinkedHashMap<>(players);next.put(id,new KnownPlayer(id,name,now));persist(claims.values(),estates,next);players.clear();players.putAll(next);
    }
    private Estate lord(UUID actor) throws Denied {Estate estate=estates.get(actor);if(estate==null)throw new Denied("이 작업은 영주만 할 수 있습니다.");return estate;}
    private void saveEstate(Estate estate) throws IOException {Map<UUID,Estate> next=new LinkedHashMap<>(estates);next.put(estate.owner,estate);persist(claims.values(),next,players);estates.clear();estates.putAll(next);}
    public synchronized void invite(UUID actor,UUID target) throws Denied,IOException {
        Estate estate=lord(actor);KnownPlayer player=players.get(target);
        if(player==null)throw new Denied("서버에서 확인한 유저만 초대할 수 있습니다.");
        if(estateFor(target)!=null)throw new Denied("이미 영지에 소속된 유저입니다.");
        List<Invitation> active=estate.invitations.stream().filter(i->i.at>=System.currentTimeMillis()-7*86400000L).toList();
        if(estate.members.size()>=EstateRules.memberLimit(progress.get(estate.owner).level))throw new Denied("영지 최대 인원은 영주를 포함해 5명입니다. 현재 정원이 찼습니다.");
        if(active.size()>=64)throw new Denied("대기 중인 초대 한도에 도달했습니다.");
        if(active.stream().anyMatch(i->i.id.equals(target)))throw new Denied("이미 초대한 유저입니다.");
        List<Invitation> next=new ArrayList<>(active);next.add(new Invitation(target,player.name,System.currentTimeMillis()));
        saveEstate(new Estate(actor,estate.name,estate.members,next,estate.announcement,estate.image,estate.home));
    }
    public synchronized void answerInvite(UUID actor,UUID owner,boolean accept) throws Denied,IOException {
        Estate estate=estates.get(owner);long cutoff=System.currentTimeMillis()-7*86400000L;
        if(estate==null||estate.invitations.stream().noneMatch(i->i.id.equals(actor)&&i.at>=cutoff))throw new Denied("유효한 초대가 없습니다. 초대는 7일간 유지됩니다.");
        if(accept&&estateFor(actor)!=null)throw new Denied("이미 소속된 영지가 있습니다.");
        if(accept&&estate.members.size()>=EstateRules.memberLimit(progress.get(estate.owner).level))throw new Denied("영지 최대 인원은 영주를 포함해 5명입니다. 현재 정원이 찼습니다.");
        List<Invitation> invitations=estate.invitations.stream().filter(i->!i.id.equals(actor)).toList();
        List<Member> members=new ArrayList<>(estate.members);
        if(accept){KnownPlayer player=players.get(actor);if(player==null)throw new Denied("플레이어 정보를 확인해주세요.");members.add(new Member(actor,player.name,Role.RESIDENT,System.currentTimeMillis()));}
        saveEstate(new Estate(owner,estate.name,members,invitations,estate.announcement,estate.image,estate.home));
    }
    public synchronized void changeRole(UUID actor,UUID target,Role role) throws Denied,IOException {
        Estate estate=lord(actor);
        if(target.equals(actor)||role==null||role==Role.LORD)throw new Denied("영주 등급은 변경하거나 다른 유저에게 부여할 수 없습니다.");
        if(estate.members.stream().noneMatch(m->m.id.equals(target)))throw new Denied("해당 마을원이 없습니다.");
        List<Member> members=estate.members.stream().map(m->m.id.equals(target)?new Member(m.id,m.name,role,m.joinedAt):m).toList();
        saveEstate(new Estate(actor,estate.name,members,estate.invitations,estate.announcement,estate.image,estate.home));
    }
    public synchronized void kick(UUID actor,UUID target) throws Denied,IOException {
        Estate estate=lord(actor);if(target.equals(actor))throw new Denied("영주는 추방할 수 없습니다.");
        if(estate.members.stream().noneMatch(m->m.id.equals(target)))throw new Denied("해당 마을원이 없습니다.");
        saveEstate(new Estate(actor,estate.name,estate.members.stream().filter(m->!m.id.equals(target)).toList(),estate.invitations,estate.announcement,estate.image,estate.home));
    }
    public synchronized void updateNotice(UUID actor,String text) throws Denied,IOException {
        Estate estate=lord(actor);if(text==null||text.length()>1000)throw new Denied("공지는 1000자 이내로 작성해주세요.");
        saveEstate(new Estate(actor,estate.name,estate.members,estate.invitations,text,estate.image,estate.home));
    }
    public synchronized void updateImage(UUID actor,String image) throws Denied,IOException {
        Estate estate=lord(actor);
        if(image==null||image.length()>18000)throw new Denied("이미지 크기가 너무 큽니다.");
        if(!image.isEmpty())try{
            if(!image.startsWith("data:image/jpeg;base64,"))throw new IllegalArgumentException();
            byte[] bytes=Base64.getDecoder().decode(image.substring(23));
            try(var input=javax.imageio.ImageIO.createImageInputStream(new java.io.ByteArrayInputStream(bytes))){
                var readers=javax.imageio.ImageIO.getImageReaders(input);if(!readers.hasNext())throw new IllegalArgumentException();
                var reader=readers.next();try{reader.setInput(input);if(!reader.getFormatName().equalsIgnoreCase("JPEG")||reader.getWidth(0)>1024||reader.getHeight(0)>768)throw new IllegalArgumentException();}finally{reader.dispose();}
            }
        }catch(Exception invalid){throw new Denied("올바른 JPEG 이미지를 선택해주세요.");}
        saveEstate(new Estate(actor,estate.name,estate.members,estate.invitations,estate.announcement,image,estate.home));
    }
    public synchronized void deleteEstate(UUID actor,String typedName) throws Denied,IOException {
        Estate estate=lord(actor);if(!estate.name.equals(typedName))throw new Denied("영지 이름이 일치하지 않습니다. 이름을 정확히 입력해주세요.");
        Map<UUID,Estate> next=new LinkedHashMap<>(estates);next.remove(actor);
        Map<Key,Claim> nextClaims=new LinkedHashMap<>(claims);nextClaims.values().removeIf(c->c.owner.equals(actor));
        Map<UUID,Progress> nextProgress=new LinkedHashMap<>(progress);nextProgress.remove(actor);
        persist(nextClaims.values(),next,players,nextProgress);progress.clear();progress.putAll(nextProgress);claims.clear();claims.putAll(nextClaims);estates.clear();estates.putAll(next);
    }
    public synchronized Progress progress(UUID owner){return progress.get(owner);}
    private static List<VaultEntry> appendLedger(List<VaultEntry> history,VaultEntry entry){List<VaultEntry> result=new ArrayList<>(history);result.add(entry);return List.copyOf(result.subList(Math.max(0,result.size()-50),result.size()));}
    private void saveProgress(Progress value) throws IOException {Map<UUID,Progress> next=new LinkedHashMap<>(progress);next.put(value.owner,value);persist(claims.values(),estates,players,next);progress.clear();progress.putAll(next);}
    public synchronized void upgrade(UUID actor,int expectedLevel) throws Denied,IOException {
        Estate estate=lord(actor);Progress value=progress.get(estate.owner);
        if(value.level!=expectedLevel)throw new Denied("영지 레벨이 변경되었습니다. 새로고침 후 다시 확인해주세요.");
        if(value.level>=EstateRules.MAX_LEVEL)throw new Denied("이미 최대 레벨 10입니다.");
        int next=value.level+1;long cost=EstateRules.cost(next);
        if(value.treasury<cost)throw new Denied("영지 금고 잔액이 부족합니다.");
        saveProgress(new Progress(value.owner,next,value.treasury-cost,value.purchasedChunks,appendLedger(value.ledger,new VaultEntry("UPGRADE",cost,next,actor,System.currentTimeMillis()))));
    }
    public synchronized long wallet(UUID player){return balances.getOrDefault(player,0L);}
    public synchronized void deposit(UUID actor,long amount) throws Denied,IOException {
        Estate estate=estateFor(actor);if(estate==null)throw new Denied("소속된 영지가 없습니다.");
        if(amount<=0||amount>EstateRules.MAX_MONEY)throw new Denied("입금 금액은 1원 이상 정수로 입력해주세요.");
        if(wallet(actor)<amount)throw new Denied("개인 재화가 부족합니다.");
        Progress value=progress.get(estate.owner);if(value.treasury>EstateRules.MAX_MONEY-amount)throw new Denied("금고 한도를 초과합니다.");
        Progress updated=new Progress(value.owner,value.level,value.treasury+amount,value.purchasedChunks,appendLedger(value.ledger,new VaultEntry("DEPOSIT",amount,value.level,actor,System.currentTimeMillis())));
        Map<UUID,Progress> nextProgress=new LinkedHashMap<>(progress);nextProgress.put(value.owner,updated);Map<UUID,Long> nextBalances=new LinkedHashMap<>(balances);nextBalances.put(actor,wallet(actor)-amount);
        persist(claims.values(),estates,players,nextProgress,nextBalances);progress.clear();progress.putAll(nextProgress);balances.clear();balances.putAll(nextBalances);
    }
    /** Trusted shop debit/credit. No browser-supplied amount is ever forwarded here. */
    public synchronized void shopAdjust(UUID player,long delta) throws Denied,IOException {
        if(player==null)throw new Denied("플레이어를 확인해주세요.");
        long current=wallet(player),next;
        try{next=Math.addExact(current,delta);}catch(ArithmeticException invalid){throw new Denied("재화 한도를 초과합니다.");}
        if(next<0)throw new Denied("개인 재화가 부족합니다.");
        if(next>EstateRules.MAX_MONEY)throw new Denied("재화 한도를 초과합니다.");
        Map<UUID,Long> values=new LinkedHashMap<>(balances);values.put(player,next);
        persist(claims.values(),estates,players,progress,values);balances.clear();balances.putAll(values);
    }
    /** Trusted server-side credit; browser events never mint personal currency. */
    public synchronized void creditWallet(UUID player,long amount) throws Denied,IOException {
        if(player==null||amount<=0||amount>EstateRules.MAX_MONEY||wallet(player)>EstateRules.MAX_MONEY-amount)throw new Denied("지급 금액이 올바르지 않습니다.");
        Map<UUID,Long> next=new LinkedHashMap<>(balances);next.put(player,wallet(player)+amount);persist(claims.values(),estates,players,progress,next);balances.clear();balances.putAll(next);
    }
    /** Trusted server integration point; never exposed as a browser-supplied credit. */
    public synchronized void creditTreasury(UUID owner,long amount,UUID actor,boolean testCredit) throws Denied,IOException {
        if(!estates.containsKey(owner)||actor==null)throw new Denied("영지를 확인해주세요.");
        if(amount<=0||amount>EstateRules.MAX_MONEY)throw new Denied("입금 금액이 올바르지 않습니다.");
        Progress value=progress.get(owner);if(value.treasury>EstateRules.MAX_MONEY-amount)throw new Denied("금고 한도를 초과합니다.");
        saveProgress(new Progress(owner,value.level,value.treasury+amount,value.purchasedChunks,appendLedger(value.ledger,new VaultEntry(testCredit?"TEST_CREDIT":"DEPOSIT",amount,value.level,actor,System.currentTimeMillis()))));
    }
    private void persist(Collection<Claim> values) throws IOException {persist(values,estates,players);}
    private void persist(Collection<Claim> values,Map<UUID,Estate> estateValues,Map<UUID,KnownPlayer> playerValues) throws IOException {
        persist(values,estateValues,playerValues,progress);
    }
    private void persist(Collection<Claim> values,Map<UUID,Estate> estateValues,Map<UUID,KnownPlayer> playerValues,Map<UUID,Progress> progressValues) throws IOException {
        persist(values,estateValues,playerValues,progressValues,balances);
    }
    private void persist(Collection<Claim> values,Map<UUID,Estate> estateValues,Map<UUID,KnownPlayer> playerValues,Map<UUID,Progress> progressValues,Map<UUID,Long> balanceValues) throws IOException {
        State state=new State();state.balances=balanceValues.entrySet().stream().map(e->new Wallet(e.getKey(),e.getValue())).toList();state.progress=new ArrayList<>(progressValues.values());state.claims=new ArrayList<>(values);state.estates=new ArrayList<>(estateValues.values());state.players=new ArrayList<>(playerValues.values());
        byte[] bytes=GSON.toJson(state).getBytes(StandardCharsets.UTF_8);
        Files.createDirectories(path.getParent());Path temporary=path.resolveSibling(path.getFileName()+".tmp-"+UUID.randomUUID());
        try {
            try(FileChannel file=FileChannel.open(temporary,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
                ByteBuffer buffer=ByteBuffer.wrap(bytes);while(buffer.hasRemaining())file.write(buffer);file.force(true);
            }
            // Keep one prior valid state for operator recovery, never silently replace corrupt data.
            if(Files.exists(path))Files.copy(path,path.resolveSibling(path.getFileName()+".bak"),StandardCopyOption.REPLACE_EXISTING);
            try {Files.move(temporary,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}
            catch(AtomicMoveNotSupportedException error){Files.move(temporary,path,StandardCopyOption.REPLACE_EXISTING);}
        } finally {Files.deleteIfExists(temporary);}
    }
}
