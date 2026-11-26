package space.pocketmate.estates;

import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.text.Text;
import org.slf4j.LoggerFactory;

import static net.minecraft.server.command.CommandManager.argument;
import static net.minecraft.server.command.CommandManager.literal;

final class PixelmonConfigCommand {
    private static final String CONFIG_API = "com.pixelmonmod.pixelmon.api.config.";
    private static final String YAML_CONFIG = CONFIG_API + "api.yaml.AbstractYamlConfig";
    private static final String VALUE_REFERENCE = "info.pixelmon.repack.org.spongepowered.reference.ValueReference";
    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger("pocketmate-pixelmon-config");

    private record Setting(String key, String configGetter, String field, int min, int max, boolean ticks) {}

    private static final Setting[] SETTINGS = {
        new Setting("exp-modifier", "getBattle", "expModifier", 0, 100, false),
        new Setting("legendary-spawn-chance", "getSpawningLegendary", "legendarySpawnChance", 0, 1, false),
        new Setting("legendary-spawn-ticks", "getSpawningLegendary", "legendarySpawnTicks", 1, 10_000_000, true),
        new Setting("boss-spawn-chance", "getSpawningBoss", "bossSpawnChance", 0, 1, false),
        new Setting("boss-spawn-ticks", "getSpawningBoss", "bossSpawnTicks", 1, 10_000_000, true),
        new Setting("spawn-ticks-player-multiplier", "getSpawningLegendary", "spawnTicksPlayerMultiplier", 0, 1, false)
    };

    private PixelmonConfigCommand() {}

    static void register() {
        NeoEvents.commands((dispatcher, access, environment) -> {
            if (!net.neoforged.fml.ModList.get().isLoaded("pixelmon")) return;
            var get = literal("get");
            var set = literal("set");
            for (Setting setting : SETTINGS) {
                get.then(literal(setting.key()).executes(ctx -> read(ctx.getSource(), setting)));
                set.then(setNode(setting));
            }
            dispatcher.register(literal("pixelconfig").requires(source -> source.hasPermissionLevel(2))
                .then(literal("list").executes(ctx -> {
                    int count = 0;
                    for (Setting setting : SETTINGS) count += read(ctx.getSource(), setting);
                    return count;
                }))
                .then(get).then(set));
        });
    }

    private static LiteralArgumentBuilder<ServerCommandSource> setNode(Setting setting) {
        var node = literal(setting.key());
        if (setting.ticks()) {
            return node.then(argument("value", IntegerArgumentType.integer(setting.min(), setting.max()))
                .executes(ctx -> write(ctx.getSource(), setting, IntegerArgumentType.getInteger(ctx, "value"))));
        }
        return node.then(argument("value", DoubleArgumentType.doubleArg(setting.min(), setting.max()))
            .executes(ctx -> write(ctx.getSource(), setting, (float) DoubleArgumentType.getDouble(ctx, "value"))));
    }

    private static Object config(Setting setting) throws ReflectiveOperationException {
        return Class.forName(CONFIG_API + "PixelmonConfigProxy").getMethod(setting.configGetter()).invoke(null);
    }

    private static int read(ServerCommandSource source, Setting setting) {
        try {
            Object config = config(setting);
            var field = config.getClass().getDeclaredField(setting.field());
            field.setAccessible(true);
            var value = field.get(config);
            source.sendFeedback(() -> Text.literal(setting.key() + " = " + value), false);
            return 1;
        } catch (ReflectiveOperationException | RuntimeException failure) {
            LOG.error("Could not read Pixelmon setting {}", setting.key(), failure);
            source.sendError(Text.literal("Pixelmon 설정을 읽지 못했습니다. 서버 로그를 확인해 주세요."));
            return 0;
        }
    }

    private static int write(ServerCommandSource source, Setting setting, Number value) {
        if (!Double.isFinite(value.doubleValue())) {
            source.sendError(Text.literal("유한한 숫자를 입력해 주세요."));
            return 0;
        }
        try {
            Object config = config(setting);
            var field = config.getClass().getDeclaredField(setting.field());
            field.setAccessible(true);
            var referenceField = Class.forName(YAML_CONFIG).getDeclaredField("config");
            referenceField.setAccessible(true);
            Object reference = referenceField.get(config);
            var api = Class.forName(VALUE_REFERENCE);
            var save = api.getMethod("setAndSave", Object.class);
            var restore = api.getMethod("set", Object.class);
            Object previous = field.get(config);
            field.set(config, value);
            try {
                if (!Boolean.TRUE.equals(save.invoke(reference, config))) {
                    throw new IllegalStateException("Pixelmon configuration save failed");
                }
            } catch (ReflectiveOperationException | RuntimeException failure) {
                field.set(config, previous);
                try {
                    restore.invoke(reference, config);
                } catch (ReflectiveOperationException | RuntimeException restoreFailure) {
                    failure.addSuppressed(restoreFailure);
                }
                throw failure;
            }
            LOG.info("{} changed {} from {} to {}", source.getName(), setting.key(), previous, value);
            source.sendFeedback(() -> Text.literal(setting.key() + " = " + value + " (적용 및 저장 완료)"), false);
            return 1;
        } catch (ReflectiveOperationException | RuntimeException failure) {
            LOG.error("Could not save Pixelmon setting {}", setting.key(), failure);
            source.sendError(Text.literal("Pixelmon 설정을 저장하지 못했습니다. 서버 로그를 확인해 주세요."));
            return 0;
        }
    }
}
