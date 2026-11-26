package space.pocketmate.estates;

import java.util.Locale;
import java.util.Optional;
import net.minecraft.network.packet.s2c.play.ScoreboardDisplayS2CPacket;
import net.minecraft.network.packet.s2c.play.ScoreboardObjectiveUpdateS2CPacket;
import net.minecraft.network.packet.s2c.play.ScoreboardScoreUpdateS2CPacket;
import net.minecraft.scoreboard.Scoreboard;
import net.minecraft.scoreboard.ScoreboardCriterion;
import net.minecraft.scoreboard.ScoreboardDisplaySlot;
import net.minecraft.scoreboard.ScoreboardObjective;
import net.minecraft.scoreboard.number.FixedNumberFormat;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

final class WalletSidebar {
    private static final String ID = "pm_wallet";
    private static final ScoreboardObjective OBJECTIVE = new ScoreboardObjective(
        new Scoreboard(), ID, ScoreboardCriterion.DUMMY, Text.literal("포켓메이트"),
        ScoreboardCriterion.RenderType.INTEGER, false, null);

    private WalletSidebar() {}

    static void show(ServerPlayerEntity player, long balance, boolean firstDisplay) {
        if (firstDisplay) player.networkHandler.sendPacket(new ScoreboardObjectiveUpdateS2CPacket(OBJECTIVE, 0));
        Text amount = Text.literal(String.format(Locale.KOREA, "%,d원", balance)).formatted(Formatting.GREEN);
        player.networkHandler.sendPacket(new ScoreboardScoreUpdateS2CPacket(
            "pm_balance", ID, 0, Optional.of(Text.literal("보유 재화")), Optional.of(new FixedNumberFormat(amount))));
        if (firstDisplay) player.networkHandler.sendPacket(new ScoreboardDisplayS2CPacket(ScoreboardDisplaySlot.SIDEBAR, OBJECTIVE));
    }

    static void remove(ServerPlayerEntity player) {
        player.networkHandler.sendPacket(new ScoreboardObjectiveUpdateS2CPacket(OBJECTIVE, 1));
    }
}
