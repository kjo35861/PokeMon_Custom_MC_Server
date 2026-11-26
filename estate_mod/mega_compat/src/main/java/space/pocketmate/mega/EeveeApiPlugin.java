package space.pocketmate.mega;

import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;
import java.util.List;
import java.util.Set;

/** Adapt EeveeMega's 9.3 BattleController calls to the 9.4 interface API.
 * No third-party classes are bundled: transformation happens on the supplied
 * version-pinned EeveeMega classes at normal Mixin load time.
 */
public final class EeveeApiPlugin implements IMixinConfigPlugin {
    public static final String CONTROLLER = "com/pixelmonmod/pixelmon/battles/controller/BattleController";

    public static int rewriteBattleApi(ClassNode node) {
        if (!node.name.startsWith("com/eeveeserver/mega/")) return 0;
        int changes = 0;
        for (var method : node.methods) {
            for (var insn : method.instructions.toArray()) {
                if (insn instanceof FieldInsnNode field && field.owner.equals(CONTROLLER)) {
                    if (field.getOpcode() != Opcodes.GETFIELD || !Set.of("globalStatusController", "participants", "battleTurn").contains(field.name)) {
                        throw new IllegalStateException("Unexpected EeveeMega BattleController field " + field.name);
                    }
                    method.instructions.set(field, new MethodInsnNode(Opcodes.INVOKEINTERFACE,
                        CONTROLLER, field.name, "()" + field.desc, true));
                    changes++;
                } else if (insn instanceof MethodInsnNode call && call.owner.equals(CONTROLLER)
                           && call.getOpcode() == Opcodes.INVOKEVIRTUAL) {
                    call.setOpcode(Opcodes.INVOKEINTERFACE);
                    call.itf = true;
                    changes++;
                }
            }
        }
        return changes;
    }

    @Override public void preApply(String target, ClassNode node, String mixin, IMixinInfo info) { rewriteBattleApi(node); }
    @Override public void onLoad(String packageName) { }
    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String target, String mixin) { return true; }
    @Override public void acceptTargets(Set<String> mine, Set<String> others) { }
    @Override public List<String> getMixins() { return null; }
    @Override public void postApply(String target, ClassNode node, String mixin, IMixinInfo info) { }
}
