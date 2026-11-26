package space.pocketmate.mega;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicInterpreter;
import java.util.Set;
import java.util.zip.ZipFile;
import static org.junit.jupiter.api.Assertions.*;

class EeveeApiPluginTest {
    private static final Set<String> EXPECTED = Set.of("ability/Eelevate", "ability/MegaSol", "ability/SpicySpray",
        "ability/TeraShift", "ability/TeraShell", "BattleAbilityCommand", "WeatherCommand");

    @Test void transformsAllActualLegacyInstructionsAndPreservesStackShape() throws Exception {
        int classes = 0, instructions = 0;
        try (var original = new ZipFile(System.getProperty("eeveemegaJar"));
             var core = new ZipFile(System.getProperty("pixelmonJar"))) {
            for (String suffix : EXPECTED) {
                var node = read(original, "com/eeveeserver/mega/" + suffix);
                int changes = EeveeApiPlugin.rewriteBattleApi(node);
                assertTrue(changes > 0, suffix);
                instructions += changes; classes++;
                for (var method : node.methods) {
                    for (var insn : method.instructions.toArray()) {
                        if (insn instanceof FieldInsnNode f) assertNotEquals(EeveeApiPlugin.CONTROLLER, f.owner);
                        if (insn instanceof MethodInsnNode m && m.owner.equals(EeveeApiPlugin.CONTROLLER)) {
                            assertEquals(Opcodes.INVOKEINTERFACE,m.getOpcode());assertTrue(m.itf);
                            assertTrue(hasMethod(core,EeveeApiPlugin.CONTROLLER,m.name,m.desc,new java.util.HashSet<>()), m.name+m.desc);
                        }
                    }
                    if ((method.access & (Opcodes.ACC_ABSTRACT|Opcodes.ACC_NATIVE)) == 0)
                        new Analyzer<>(new BasicInterpreter()).analyze(node.name,method);
                }
                var writer = new ClassWriter(0);node.accept(writer);
                assertDoesNotThrow(() -> new ClassReader(writer.toByteArray()));
            }
        }
        assertEquals(7,classes);assertEquals(12,instructions);
    }

    @Test void transformationIsIdempotentAndLeavesOtherModsUntouched() throws Exception {
        try (var original = new ZipFile(System.getProperty("eeveemegaJar"))) {
            var node=read(original,"com/eeveeserver/mega/ability/MegaSol");
            assertTrue(EeveeApiPlugin.rewriteBattleApi(node)>0);
            assertEquals(0,EeveeApiPlugin.rewriteBattleApi(node));
            node.name="another/mod/Example";
            assertEquals(0,EeveeApiPlugin.rewriteBattleApi(node));
        }
    }

    private static ClassNode read(ZipFile file,String name) throws Exception {
        var entry=file.getEntry(name+".class");assertNotNull(entry,name);
        var node=new ClassNode();new ClassReader(file.getInputStream(entry).readAllBytes()).accept(node,0);return node;
    }
    private static boolean hasMethod(ZipFile file,String owner,String name,String desc,Set<String> seen) throws Exception {
        if (!seen.add(owner) || file.getEntry(owner+".class")==null) return false;
        var node=read(file,owner);
        if (node.methods.stream().anyMatch(m->m.name.equals(name)&&m.desc.equals(desc))) return true;
        for (String parent:node.interfaces) if (hasMethod(file,parent,name,desc,seen)) return true;
        return node.superName!=null && hasMethod(file,node.superName,name,desc,seen);
    }
}
