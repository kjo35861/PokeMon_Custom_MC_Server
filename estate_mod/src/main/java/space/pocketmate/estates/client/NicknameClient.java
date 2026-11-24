package space.pocketmate.estates.client;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.*;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.*;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.text.Text;
import space.pocketmate.estates.NicknamePayload;
public final class NicknameClient implements ClientModInitializer {
    private static NicknamePayload pending;
    public void onInitializeClient(){
        ClientPlayNetworking.registerGlobalReceiver(NicknamePayload.ID,(data,context)->context.client().execute(()->{pending=data;if(context.client().currentScreen instanceof NicknameScreen screen){if(!data.required()){context.client().setScreen(null);pending=null;}else screen.feedback(data.message());}}));
        ClientPlayConnectionEvents.DISCONNECT.register((handler,client)->pending=null);
        ClientTickEvents.END_CLIENT_TICK.register(client->{if(pending!=null&&client.world!=null&&client.player!=null){var data=pending;pending=null;if(data.required())client.setScreen(new NicknameScreen(data.message()));}});
    }
    private static final class NicknameScreen extends Screen {
        private TextFieldWidget field;private ButtonWidget save;private String message;private boolean waiting;
        NicknameScreen(String message){super(Text.literal("포켓메이트에 오신 것을 환영합니다"));this.message=message;}
        protected void init(){
            field=new TextFieldWidget(textRenderer,width/2-120,height/2-10,240,24,Text.literal("닉네임"));field.setMaxLength(24);addDrawableChild(field);setInitialFocus(field);
            save=addDrawableChild(ButtonWidget.builder(Text.literal("닉네임 지정"),button->{
                if(client.getNetworkHandler()==null)return;
                try{String name=space.pocketmate.estates.NicknameStore.normalize(field.getText());waiting=true;save.active=false;client.getNetworkHandler().sendChatCommand("닉네임 설정 "+name);}catch(IllegalArgumentException invalid){feedback(invalid.getMessage());}
            }).dimensions(width/2-120,height/2+30,240,24).build());save.active=!waiting;
        }
        void feedback(String message){this.message=message;waiting=false;if(save!=null)save.active=true;}
        public boolean shouldCloseOnEsc(){return false;}
        public boolean shouldPause(){return false;}
        public void render(DrawContext context,int mouseX,int mouseY,float delta){
            renderBackground(context,mouseX,mouseY,delta);super.render(context,mouseX,mouseY,delta);
            context.drawCenteredTextWithShadow(textRenderer,title,width/2,height/2-70,0xffe0a0);
            context.drawCenteredTextWithShadow(textRenderer,"서버에서 사용할 이름 · 한글/영문/숫자/밑줄 2~12자",width/2,height/2-45,0xd1ded6);
            context.drawCenteredTextWithShadow(textRenderer,Text.literal(message),width/2,height/2+70,0xff9999);
        }
    }
}
