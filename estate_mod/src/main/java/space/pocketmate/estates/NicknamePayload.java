package space.pocketmate.estates;
import net.minecraft.network.RegistryByteBuf;
import net.minecraft.network.codec.PacketCodec;
import net.minecraft.network.packet.CustomPayload;
import net.minecraft.util.Identifier;
public record NicknamePayload(boolean required,String message) implements CustomPayload {
    public static final Id<NicknamePayload> ID=new Id<>(Identifier.of("pocketmate","nickname"));
    public static final PacketCodec<RegistryByteBuf,NicknamePayload> CODEC=PacketCodec.of((value,buf)->{buf.writeBoolean(value.required());buf.writeString(value.message(),256);},buf->new NicknamePayload(buf.readBoolean(),buf.readString(256)));
    public Id<? extends CustomPayload> getId(){return ID;}
}
