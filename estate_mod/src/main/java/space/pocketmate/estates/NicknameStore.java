package space.pocketmate.estates;
import com.google.gson.*;
import java.nio.file.*;
import java.io.IOException;
import java.text.Normalizer;
import java.util.*;

/** UUID ownership; immutable first registration, atomically persisted. */
public final class NicknameStore {
    private final Path path;
    private final Map<UUID,String> names=new LinkedHashMap<>();
    public NicknameStore(Path path)throws IOException{
        this.path=path;
        if(!Files.exists(path))return;
        try{
            JsonObject root=JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            if(root.get("formatVersion").getAsInt()!=1)throw new IllegalArgumentException();
            for(var entry:root.getAsJsonObject("names").entrySet()){
                String name=normalize(entry.getValue().getAsString());
                if(resolve(name)!=null)throw new IllegalArgumentException();
                names.put(UUID.fromString(entry.getKey()),name);
            }
        }catch(RuntimeException bad){throw new IOException("Invalid nickname store; refusing reset",bad);}
    }
    public static String normalize(String name){
        String n=Normalizer.normalize(name,Normalizer.Form.NFC);
        if(!n.matches("[가-힣A-Za-z0-9_]{2,12}"))throw new IllegalArgumentException("닉네임은 한글·영문·숫자·밑줄로 2~12자 입력해주세요.");
        return n;
    }
    public String get(UUID id){return names.get(id);}
    public UUID resolve(String name){return names.entrySet().stream().filter(e->e.getValue().equalsIgnoreCase(Normalizer.normalize(name,Normalizer.Form.NFC))).map(Map.Entry::getKey).findFirst().orElse(null);}
    public void register(UUID id,String input,Map<UUID,String> accounts)throws IOException{
        if(names.containsKey(id))throw new IllegalArgumentException("이미 닉네임을 지정했습니다.");
        String name=normalize(input);UUID owner=resolve(name);
        if(owner!=null&&!owner.equals(id))throw new IllegalArgumentException("이미 사용 중인 닉네임입니다.");
        if(accounts.entrySet().stream().anyMatch(e->!e.getKey().equals(id)&&e.getValue().equalsIgnoreCase(name)))throw new IllegalArgumentException("다른 플레이어의 계정명은 사용할 수 없습니다.");
        var next=new LinkedHashMap<>(names);next.put(id,name);
        JsonObject root=new JsonObject(),values=new JsonObject();root.addProperty("formatVersion",1);next.forEach((key,value)->values.addProperty(key.toString(),value));root.add("names",values);
        Files.createDirectories(path.getParent());Path tmp=Files.createTempFile(path.getParent(),"nicknames-",".tmp");
        try{
            Files.writeString(tmp,new GsonBuilder().setPrettyPrinting().create().toJson(root));
            try{Files.move(tmp,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}catch(AtomicMoveNotSupportedException unsupported){Files.move(tmp,path,StandardCopyOption.REPLACE_EXISTING);}
            names.clear();names.putAll(next);
        }finally{Files.deleteIfExists(tmp);}
    }
}
