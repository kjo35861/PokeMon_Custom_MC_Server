package space.pocketmate.mega.mixin;

import org.spongepowered.asm.mixin.Mixin;

// Empty mixins select the exact original classes for EeveeApiPlugin.preApply.
@Mixin(targets = "com.eeveeserver.mega.ability.Eelevate", remap = false)
abstract class EelevateApiMixin { }
@Mixin(targets = "com.eeveeserver.mega.ability.MegaSol", remap = false)
abstract class MegaSolApiMixin { }
@Mixin(targets = "com.eeveeserver.mega.ability.SpicySpray", remap = false)
abstract class SpicySprayApiMixin { }
@Mixin(targets = "com.eeveeserver.mega.ability.TeraShift", remap = false)
abstract class TeraShiftApiMixin { }
@Mixin(targets = "com.eeveeserver.mega.ability.TeraShell", remap = false)
abstract class TeraShellApiMixin { }
@Mixin(targets = "com.eeveeserver.mega.BattleAbilityCommand", remap = false)
abstract class BattleAbilityApiMixin { }
@Mixin(targets = "com.eeveeserver.mega.WeatherCommand", remap = false)
abstract class WeatherApiMixin { }
