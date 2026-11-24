package space.pocketmate.estates.mixin;
import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.command.EntitySelectorReader;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
@Mixin(EntitySelectorReader.class)
public abstract class NicknameSelectorMixin {
    @Redirect(method="readRegular",at=@At(value="INVOKE",target="Lcom/mojang/brigadier/StringReader;readString()Ljava/lang/String;",remap=false))
    private String pocketmate$unicode(StringReader reader)throws CommandSyntaxException{
        if(reader.canRead()&&StringReader.isQuotedStringStart(reader.peek()))return reader.readString();
        int start=reader.getCursor(),end=start;String input=reader.getString();boolean korean=false;
        while(end<input.length()){
            char c=input.charAt(end);
            if(c>='가'&&c<='힣')korean=true;
            else if(!StringReader.isAllowedInUnquotedString(c))break;
            end++;
        }
        if(korean){reader.setCursor(end);return input.substring(start,end);}
        return reader.readString();
    }
}
