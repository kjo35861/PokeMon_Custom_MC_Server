using System.Linq;
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.Win32;

[assembly: AssemblyTitle("포켓메이트 런처")]
[assembly: AssemblyProduct("Pocketmate Launcher")]
[assembly: AssemblyDescription("친구들과 함께하는 포켓몬 모험, 포켓메이트")]
[assembly: AssemblyVersion("0.3.1.0")]
[assembly: AssemblyFileVersion("0.3.1.0")]

namespace Snowfrost
{
    public sealed class Settings
    {
        public const string DefaultName = "포켓메이트";
        public string DisplayName { get; set; }
        public string LauncherPath { get; set; }
        public string BackgroundPath { get; set; }
        public bool MinimizeAfterLaunch { get; set; }
        public int LaunchCount { get; set; }
        public string LastOpenedUtc { get; set; }
        public string MicrosoftClientId { get; set; }
        public string UpdateManifestUrl { get; set; }
        public string PrismPath { get; set; }
        public string PrismDataPath { get; set; }
        public string PrismInstanceId { get; set; }
        public string JavaPath { get; set; }
        public int MemoryMB { get; set; }
        public Settings() { DisplayName = DefaultName; LauncherPath = ""; BackgroundPath = ""; LastOpenedUtc = ""; MicrosoftClientId = ""; UpdateManifestUrl = ""; JavaPath = ""; MemoryMB = 4096; PrismPath = ""; PrismDataPath = ""; PrismInstanceId = ""; }
    }

    public sealed class SettingsStore
    {
        public readonly string DirectoryPath;
        public SettingsStore(string path) { DirectoryPath = Path.GetFullPath(path); }
        public Settings Load()
        {
            string file = Path.Combine(DirectoryPath, "settings.json");
            if (!File.Exists(file)) return ApplyConfig(new Settings());
            try
            {
                Settings value = new JavaScriptSerializer().Deserialize<Settings>(File.ReadAllText(file, Encoding.UTF8));
                if (value == null) return new Settings();
                if (String.IsNullOrWhiteSpace(value.DisplayName) || value.DisplayName == "나무온라인" ||
                    value.DisplayName == "나무서버" || value.DisplayName == "나무 서버")
                {
                    value.DisplayName = Settings.DefaultName;
                    try { Save(value); } catch (Exception error) { Log("Brand name update", error); }
                }
                if (value.LaunchCount < 0) value.LaunchCount = 0;
                return ApplyConfig(value);
            }
            catch (Exception error) { Log("Settings read", error); return new Settings(); }
        }
        Settings ApplyConfig(Settings settings)
        {
            string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"launcher-config.json");
            if (File.Exists(path))
            {
                object config = Json.Parse(File.ReadAllText(path,Encoding.UTF8));
                string version = Json.Text(config,"minecraftVersion");
                if (version.Length != 0 && version != GameInstaller.Version) throw new InvalidDataException("이 런처는 Minecraft 1.21.1 전용입니다.");
                if (String.IsNullOrWhiteSpace(settings.MicrosoftClientId)) settings.MicrosoftClientId = Json.Text(config,"microsoftClientId");
                if (String.IsNullOrWhiteSpace(settings.UpdateManifestUrl)) settings.UpdateManifestUrl = Json.Text(config,"updateManifestUrl");
                if (String.IsNullOrWhiteSpace(settings.PrismPath)) settings.PrismPath=Json.Text(config,"prismPath");
                if (String.IsNullOrWhiteSpace(settings.PrismDataPath)) settings.PrismDataPath=Json.Text(config,"prismDataPath");
                if (String.IsNullOrWhiteSpace(settings.PrismInstanceId)) settings.PrismInstanceId=Json.Text(config,"prismInstanceId");
            }
            if (settings.MemoryMB < 1024 || settings.MemoryMB > 16384) settings.MemoryMB = 4096;
            return settings;
        }
        public void Save(Settings settings)
        {
            Directory.CreateDirectory(DirectoryPath);
            string file = Path.Combine(DirectoryPath, "settings.json");
            string temporary = Path.Combine(DirectoryPath, "settings.json.tmp");
            File.WriteAllText(temporary, new JavaScriptSerializer().Serialize(settings), new UTF8Encoding(false));
            if (File.Exists(file)) File.Replace(temporary, file, null);
            else File.Move(temporary, file);
        }
        public void Log(string operation, Exception error)
        {
            try
            {
                Directory.CreateDirectory(DirectoryPath);
                File.AppendAllText(Path.Combine(DirectoryPath, "launcher.log"), DateTime.UtcNow.ToString("O") + " " + operation + ": " + error.Message + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }
    }

    public sealed class Launcher
    {
        public readonly Window Window;
        readonly SettingsStore store;
        Settings settings;
        bool busy;
        bool checking;
        UpdateService updates;
        PrismTarget vanillaTarget, prismTarget;
        UpdatePlan updatePlan;
        string checkError;
        Process gameProcess;
        CancellationTokenSource work;
        bool closingRequested;
        readonly bool smokeTest;
        readonly string previewPath;
        readonly DispatcherTimer relativeClock;

        T Get<T>(string name) where T : class { return Window.FindName(name) as T; }
        void On(string name, RoutedEventHandler action) { Get<Button>(name).Click += action; }

        public Launcher(SettingsStore settingsStore, string[] arguments)
        {
            store = settingsStore; settings = store.Load();
            PrismBridge.Discover(settings);
            smokeTest = Array.IndexOf(arguments, "--smoke-test") >= 0;
            previewPath = Program.Option(arguments, "--render-preview");
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Snowfrost.MainWindow.xaml"))
                Window = (Window)XamlReader.Load(stream);
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Snowfrost.LauncherIcon.ico"))
            {
                var icon = new IconBitmapDecoder(stream, BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
                var frame = icon.Frames[0];
                foreach (var candidate in icon.Frames)
                    if (candidate.PixelWidth == 48) { frame = candidate; break; }
                Get<Image>("TitleBarIcon").Source = frame;
                Window.Icon = frame;
            }
            Window.Width = Math.Min(1440, SystemParameters.WorkArea.Width * .93);
            Window.Height = Math.Min(840, SystemParameters.WorkArea.Height * .93);
            if (previewPath != null) { Window.Width = 1440; Window.Height = 840; }
            On("MinimizeButton", delegate { Window.WindowState = WindowState.Minimized; });
            On("MaximizeButton", delegate { Window.WindowState = Window.WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized; });
            On("CloseButton", delegate { Window.Close(); });
            On("LaunchButton", async delegate { await OpenGame(); });
            On("PrismLoginButton", delegate {
                try { OpenPrismForLogin(); }
                catch (Exception error) { Info("Prism 계정 연결",error.Message); }
            });
            On("SettingsButton", delegate { OpenSettings(); });
            On("CloseSettingsButton", delegate { CloseSettings(); });
            On("SaveSettingsButton", async delegate { await SaveSettings(); });
            On("BrowseLauncherButton", delegate { BrowseLauncher(); });
            On("BrowseBackgroundButton", delegate { BrowseBackground(); });
            On("ResetBackgroundButton", delegate { Get<TextBox>("BackgroundPathBox").Text = ""; });
            On("CancelWorkButton", delegate { if (work != null) work.Cancel(); });
            On("LoginGuideButton", delegate { Info("Prism 연결 안내", "Prism Launcher에 Microsoft 계정으로 한 번 로그인하고 순정 Minecraft 1.21.1 인스턴스를 만들어주세요.\n\n아래 Prism 실행 파일, 데이터 폴더, 인스턴스 ID를 확인해 저장하면 됩니다. 일반 설치는 자동으로 찾습니다.\n\nAPI 키나 Microsoft Client ID는 필요 없습니다. 게임 시작 시 포켓메이트가 Prism을 자동으로 호출합니다.\n\n서버 주소가 비어 있으면 순정 인스턴스, 주소가 있으면 별도 서버 인스턴스를 사용합니다."); });
            On("OpenMinecraftFolderButton", delegate { OpenMinecraftFolder(); });
            var packButton = Get<Button>("ClientPackButton");
            packButton.Visibility = File.Exists(LocalPackPath) ? Visibility.Visible : Visibility.Collapsed;
            packButton.Click += delegate
            {
                try { Process.Start(new ProcessStartInfo("notepad.exe",GameInstaller.Quote(LocalPackPath)) { UseShellExecute = true }); }
                catch (Exception error) { Get<TextBlock>("SettingsError").Text = error.Message; }
            };
            var statusTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
            statusTimer.Tick += async delegate { await RefreshServerPanel(); };
            Window.Loaded += async delegate { if (!smokeTest && previewPath == null) statusTimer.Start(); await RefreshServerPanel(); };
            Window.Closed += delegate { statusTimer.Stop(); };
            On("CloseInfoButton", delegate { Get<Grid>("InfoOverlay").Visibility = Visibility.Collapsed; });
            Window.PreviewKeyDown += delegate(object sender, KeyEventArgs e) {
                if (e.Key == Key.Escape) { CloseSettings(); Get<Grid>("InfoOverlay").Visibility = Visibility.Collapsed; e.Handled = true; }
            };
            Window.SizeChanged += delegate { ResizeHero(); };
            Window.Loaded += async delegate {
                ApplyAppearance();
                await CheckInstallation();
                string verifyPlay=Program.Option(arguments,"--verify-play");
                if(verifyPlay!=null){await VerifyPlay(verifyPlay);return;}
                if(Array.IndexOf(arguments,"--preview-settings")>=0) OpenSettings();
                if (smokeTest || previewPath != null)
                {
                    DispatcherTimer timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(650) };
                    timer.Tick += delegate { timer.Stop(); if (previewPath != null) Render(previewPath); Window.Close(); };
                    timer.Start();
                }
            };
            RestoreGameProcess();
            relativeClock = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
            relativeClock.Tick += delegate { UpdateActivity(); if (gameProcess != null && gameProcess.HasExited) { int code = 0; try { code = gameProcess.ExitCode; } catch (InvalidOperationException) { } gameProcess.Dispose(); gameProcess = null; Get<TextBlock>("ActionStatus").Text = code == 0 ? "게임이 종료되었습니다." : "게임이 종료되었습니다. Prism의 게임 로그를 확인해주세요."; ReadyButton(); } };
            relativeClock.Start();
            Window.Closed += delegate { relativeClock.Stop(); };
            Window.Closing += delegate(object sender,System.ComponentModel.CancelEventArgs e) { if ((busy || checking) && work != null) { closingRequested = true; work.Cancel(); e.Cancel = true; } };
        }

        void ResizeHero()
        {
            double width = Window.ActualWidth;
            double nameUnits = 0;
            foreach (char character in (settings.DisplayName ?? "")) nameUnits += character > 255 ? 1 : .55;
            double titleSize = Math.Max(62, Math.Min(96, (width - 600) * .115));
            Get<TextBlock>("HeroTitle").FontSize = Math.Min(titleSize, Math.Max(30, (width - 545) / Math.Max(1, nameUnits)));
            Grid layout = Get<Grid>("PageLayout");
            layout.ColumnDefinitions[2].Width = new GridLength(width < 1200 ? 330 : 374);
            layout.Margin = width < 1200 ? new Thickness(34, 24, 34, 42) : new Thickness(48, 34, 48, 64);
        }

        async Task VerifyPlay(string report)
        {
            try
            {
                await OpenGame();
                if(gameProcess==null || gameProcess.HasExited)throw new Exception("Game did not start from the launch action");
                for(int i=0;i<60;i++)
                {gameProcess.Refresh();if(gameProcess.MainWindowTitle.Contains("1.21.1"))break;await Task.Delay(1000);}
                if(!gameProcess.MainWindowTitle.Contains("1.21.1"))throw new Exception("Minecraft 1.21.1 window was not observed");
                string active=Get<TextBlock>("PlayLabel").Text;
                if(active!="게임 실행 중"||Get<Button>("LaunchButton").IsEnabled)throw new Exception("Running state was not reflected in the launch button");
                Render(report+".running.png");
                Process launched=gameProcess;
                if(!launched.CloseMainWindow())throw new Exception("Could not close test game normally");
                for(int i=0;i<30 && gameProcess!=null;i++)await Task.Delay(1000);
                if(gameProcess!=null||!Get<Button>("LaunchButton").IsEnabled||Get<TextBlock>("PlayLabel").Text!="게임 시작")throw new Exception("Launch button did not return to idle");
                Render(report+".idle.png");
                Json.Save(report,new{passed=true,actualGameLaunched=true,version=GameInstaller.Version,prismInstance=prismTarget.Id,runningButton=active,idleButton=Get<TextBlock>("PlayLabel").Text,launchCount=settings.LaunchCount,gameClosedNormally=true,accountFilesRead=false});
            }
            catch(Exception error){Json.Save(report,new{passed=false,error=error.ToString()});}
            finally{Window.Close();}
        }

        void ApplyAppearance()
        {
            Get<TextBlock>("HeroTitle").Text = settings.DisplayName;
            ImageSource background = null;
            if (!String.IsNullOrWhiteSpace(settings.BackgroundPath))
            {
                try { background = LoadBitmap(settings.BackgroundPath); }
                catch (Exception error) { store.Log("Background", error); }
            }
            if (background == null)
            {
                using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Snowfrost.Background.png"))
                {
                    BitmapImage image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad;
                    image.StreamSource = stream; image.EndInit(); image.Freeze(); background = image;
                }
            }
            Get<Image>("Backdrop").Source = background;
            ResizeHero(); UpdateActivity();
        }

        static BitmapImage LoadBitmap(string path)
        {
            BitmapImage image = new BitmapImage();
            using (FileStream stream = File.OpenRead(path))
            { image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad; image.StreamSource = stream; image.EndInit(); image.Freeze(); }
            return image;
        }

        void UpdateActivity()
        {
            DateTime last;
            string text = "처음 시작";
            if (DateTime.TryParse(settings.LastOpenedUtc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out last))
            {
                TimeSpan elapsed = DateTime.UtcNow - last.ToUniversalTime();
                text = elapsed.TotalMinutes < 1 ? "방금 전" : elapsed.TotalHours < 1 ? (int)elapsed.TotalMinutes + "분 전" :
                    elapsed.TotalDays < 1 ? (int)elapsed.TotalHours + "시간 전" : last.ToLocalTime().ToString("MM.dd");
            }
            Get<TextBlock>("LastLaunch").Text = text;
            Get<TextBlock>("AccountName").Text = prismTarget != null ? "Prism 연결됨" : "Prism 설정 확인";
        }

        void RestoreGameProcess()
        {
            try
            {
                string path = Path.Combine(store.DirectoryPath,"game-session.json"); if (!File.Exists(path)) return;
                object state = Json.Parse(File.ReadAllText(path));
                Process process = Process.GetProcessById((int)Json.Number(state,"pid"));
                if (!process.HasExited && process.StartTime.ToUniversalTime().Ticks == Json.Number(state,"startTicks") && process.ProcessName.StartsWith("java",StringComparison.OrdinalIgnoreCase)) gameProcess = process;
            }
            catch { }
        }
        bool PrismInstalled()
        {
            PrismBridge.Discover(settings);
            return File.Exists(settings.PrismPath);
        }
        void OpenPrismForLogin()
        {
            if (!PrismInstalled()) throw new InvalidOperationException("먼저 게임 시작 버튼으로 Prism을 설치해주세요.");
            Process.Start(new ProcessStartInfo(settings.PrismPath,
                "--dir "+GameInstaller.Quote(settings.PrismDataPath)) { UseShellExecute=true });
            Get<TextBlock>("ActionStatus").Text="Prism의 계정 메뉴에서 Microsoft 계정을 추가한 뒤 포켓메이트에서 게임 시작을 눌러주세요.";
        }
        bool showPrismLogin;
        async Task InstallPrism()
        {
            busy=true;
            ReadyButton();
            Get<ProgressBar>("PrismInstallGauge").Visibility=Visibility.Visible;
            Get<TextBlock>("PlayLabel").Text="Prism 설치 중";
            Get<TextBlock>("ActionStatus").Text="Prism을 설치하고 있습니다. Windows 권한 확인이 표시되면 안내를 따라주세요.";
            bool installed=false;
            try
            {
                string winget=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "Microsoft","WindowsApps","winget.exe");
                if(!File.Exists(winget))winget="winget.exe";
                using(var process=Process.Start(new ProcessStartInfo(winget,
                    "install --exact --id PrismLauncher.PrismLauncher --source winget --silent --disable-interactivity")
                    { UseShellExecute=false, CreateNoWindow=true, WindowStyle=ProcessWindowStyle.Hidden }))
                {
                    if(process==null)throw new InvalidOperationException("Windows 패키지 관리자를 시작하지 못했습니다.");
                    int exit=await Task.Run(()=>{process.WaitForExit();return process.ExitCode;});
                    if(!File.Exists(settings.PrismPath))settings.PrismPath="";
                    installed=PrismInstalled();
                    if(!installed)throw new InvalidOperationException("Prism 설치를 확인하지 못했습니다. Windows 앱 설치 관리자(WinGet)를 확인한 뒤 다시 시도해주세요. 종료 코드 "+exit);
                }
            }
            catch(Exception error)
            {
                store.Log("Prism install",error);
                Info("Prism 설치를 완료하지 못했어요",error.Message);
            }
            finally { Get<ProgressBar>("PrismInstallGauge").Visibility=Visibility.Collapsed;busy=false;ReadyButton(); }
            if(installed)
            {
                await CheckInstallation();
                if (checkError==null) await OpenGame();
            }
        }
        void ReadyButton()
        {
            bool running = gameProcess != null && !gameProcess.HasExited;
            Get<Button>("LaunchButton").IsEnabled = !running && !busy && !checking;
            Get<Button>("SettingsButton").IsEnabled = !busy && !checking;
            bool installed=PrismInstalled();
            Get<Button>("PrismLoginButton").Visibility=installed&&showPrismLogin?Visibility.Visible:Visibility.Collapsed;
            Get<Button>("PrismLoginButton").IsEnabled=!busy&&!checking;
            Get<TextBlock>("PlayLabel").Text = running ? "게임 실행 중" : !installed ? "게임 시작 · Prism 설치" : checkError != null ? "다시 확인" : updatePlan != null && updatePlan.Needed ? "업데이트" : "게임 시작";
            Get<System.Windows.Shapes.Path>("PlayIcon").Data = Geometry.Parse(updatePlan!=null&&updatePlan.Needed&&checkError==null ? "M 4,0 L 8,0 8,7 12,7 6,14 0,7 4,7 Z" : "M 0,0 L 0,14 11,7 Z");
        }
        void ShowProgress(WorkProgress progress)
        {
            if (!busy && !checking) return;
            Get<Grid>("WorkArea").Visibility = Visibility.Visible;
            Get<TextBlock>("ActionStatus").Text = progress.Message;
            Get<ProgressBar>("WorkProgressBar").IsIndeterminate = progress.Percent <= 0;
            Get<ProgressBar>("WorkProgressBar").Value = Math.Max(0,Math.Min(100,progress.Percent));
        }

        string LocalPackPath { get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"client-pack.json"); } }
        UpdatePlan ReadLocalPack()
        {
            var plan = updates.CheckLocal(LocalPackPath);
            if (plan.Loader != "neoforge" || plan.LoaderVersion != "21.1.248")
                throw new InvalidDataException("테스트 팩은 NeoForge 21.1.248이어야 합니다.");
            return plan;
        }
        bool refreshingPanel;
        string ServerSetting(string key)
        {
            string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "launcher-config.json");
            return File.Exists(path) ? Json.Text(Json.Parse(File.ReadAllText(path, Encoding.UTF8)), key).Trim() : "";
        }
        async Task RefreshServerPanel()
        {
            if (refreshingPanel) return;
            refreshingPanel = true;
            var list = Get<StackPanel>("NoticeList");
            var maintenance = Get<TextBlock>("MaintenanceNotice");
            try
            {
                string url = ServerSetting("noticesUrl");
                string local = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "notices.json");
                object feed = null;
                using (var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5)))
                {
                    if (url.Length != 0 && !smokeTest && previewPath == null)
                        feed = await Net.GetJson(url, timeout.Token);
                    else if (File.Exists(local)) feed = Json.Parse(File.ReadAllText(local, Encoding.UTF8));
                }
                list.Children.Clear();
                maintenance.Visibility = Visibility.Collapsed;
                foreach (object item in Json.Array(Json.Get(feed, "notices")).Take(30))
                {
                    string title = Json.Text(item,"title").Trim(), body = Json.Text(item,"body");
                    if (title.Length == 0) continue;
                    var button = new Button { Content = title, Style = (Style)Window.FindResource("NoticeButton") };
                    button.Click += delegate { Info(title, body); };
                    list.Children.Add(button);
                }
                if (list.Children.Count == 0) list.Children.Add(new TextBlock { Text = "등록된 공지가 없습니다." });
                object window = Json.Get(feed,"maintenance");
                DateTimeOffset start, end;
                if (DateTimeOffset.TryParse(Json.Text(window,"start"),out start) &&
                    DateTimeOffset.TryParse(Json.Text(window,"end"),out end) && start < end && DateTimeOffset.UtcNow < end)
                {
                    maintenance.Text = (DateTimeOffset.UtcNow >= start ? "서버 점검 중" : "서버 점검 예정") +
                        "\n" + start.ToLocalTime().ToString("MM-dd HH:mm") + " ~ " + end.ToLocalTime().ToString("MM-dd HH:mm") +
                        "\n" + Json.Text(window,"body");
                    maintenance.Visibility = Visibility.Visible;
                }
            }
            catch (Exception)
            {
                if (list.Children.Count == 0) list.Children.Add(new TextBlock { Text = "공지사항을 불러오지 못했습니다." });
            }
            try
            {
                string address = ServerSetting("serverAddress");
                Get<TextBlock>("ServerStatus").Text = address.Length == 0 || smokeTest || previewPath != null
                    ? "" : await Task.Run(() => ReadServerStatus(address));
            }
            catch (Exception) { Get<TextBlock>("ServerStatus").Text = "서버 응답 없음"; }
            finally { refreshingPanel = false; }
        }
        static string ReadServerStatus(string address)
        {
            Uri endpoint;
            if (!Uri.TryCreate("tcp://" + address,UriKind.Absolute,out endpoint) ||
                endpoint.UserInfo.Length != 0 || endpoint.AbsolutePath != "/" ||
                endpoint.Query.Length != 0 || endpoint.Fragment.Length != 0)
                throw new InvalidDataException("서버 주소를 확인해주세요.");
            string host = endpoint.DnsSafeHost;
            int port = endpoint.Port < 0 ? 25565 : endpoint.Port;
            using (var socket = new System.Net.Sockets.TcpClient())
            {
                if (!socket.ConnectAsync(host,port).Wait(2500)) throw new TimeoutException();
                socket.ReceiveTimeout = 2500;
                socket.SendTimeout = 2500;
                using (var stream = socket.GetStream())
                using (var handshake = new MemoryStream())
                {
                    WriteVarInt(handshake,0);
                    WriteVarInt(handshake,767);
                    byte[] hostname = Encoding.UTF8.GetBytes(host);
                    WriteVarInt(handshake,hostname.Length);
                    handshake.Write(hostname,0,hostname.Length);
                    handshake.WriteByte((byte)(port >> 8));
                    handshake.WriteByte((byte)port);
                    WriteVarInt(handshake,1);
                    WriteVarInt(stream,(int)handshake.Length);
                    handshake.WriteTo(stream);
                    var timer = Stopwatch.StartNew();
                    stream.Write(new byte[]{1,0},0,2);
                    int packet = ReadVarInt(stream);
                    if (packet < 2 || packet > 65536) throw new InvalidDataException();
                    if (ReadVarInt(stream) != 0) throw new InvalidDataException();
                    int length = ReadVarInt(stream);
                    if (length < 1 || length >= packet) throw new InvalidDataException();
                    byte[] bytes = new byte[length];
                    for (int offset = 0; offset < bytes.Length;)
                    {
                        int count = stream.Read(bytes,offset,bytes.Length-offset);
                        if (count == 0) throw new EndOfStreamException();
                        offset += count;
                    }
                    object players = Json.Get(Json.Parse(Encoding.UTF8.GetString(bytes)),"players");
                    return "서버 온라인 · " + Json.Get(players,"online") + "/" + Json.Get(players,"max") +
                        "명 · " + timer.ElapsedMilliseconds + " ms";
                }
            }
        }
        static void WriteVarInt(Stream stream,int value)
        {
            uint remaining = (uint)value;
            while (remaining > 127) { stream.WriteByte((byte)(remaining | 128)); remaining >>= 7; }
            stream.WriteByte((byte)remaining);
        }
        static int ReadVarInt(Stream stream)
        {
            int value = 0;
            for (int shift = 0; shift < 32; shift += 7)
            {
                int next = stream.ReadByte();
                if (next < 0) throw new EndOfStreamException();
                value |= (next & 127) << shift;
                if ((next & 128) == 0) return value;
            }
            throw new InvalidDataException();
        }
        async Task CheckInstallation()
        {
            if (busy || checking) return;
            checking = true; work = new CancellationTokenSource(); checkError = null; ReadyButton();
            Get<TextBlock>("PlayLabel").Text = "업데이트 확인 중";
            Get<TextBlock>("ActionStatus").Text = "서버의 최신 파일 목록을 확인하고 있습니다.";
            try
            {
                CancellationToken token = work.Token;
                prismTarget=null;
                string localTestId = ServerSetting("localTestInstanceId");
                bool localTest = localTestId.Length != 0;
                bool server=!localTest && !String.IsNullOrWhiteSpace(settings.UpdateManifestUrl);
                vanillaTarget=localTest?null:await Task.Run(()=>PrismBridge.Resolve(settings));
                prismTarget=localTest?await Task.Run(()=>PrismBridge.EnsureNeoForgeClient(settings,localTestId,ServerSetting("serverAddress")))
                    :server?PrismBridge.ServerTarget(vanillaTarget,store.DirectoryPath):vanillaTarget;
                if(localTest&&!File.Exists(LocalPackPath))throw new InvalidDataException("client-pack.json이 없습니다. 배포 ZIP을 전부 풀어주세요.");
                if(server) await Task.Run(()=>PrismBridge.EnsureServer(prismTarget,vanillaTarget));
                updates=new UpdateService(Path.Combine(store.DirectoryPath,"prism",PrismBridge.Key(prismTarget.Root)),prismTarget.GameRoot);
                updatePlan = localTest && File.Exists(LocalPackPath) ? await Task.Run(() => ReadLocalPack(),token)
                    : await Task.Run(async delegate { return await updates.Check(localTest ? "" : settings.UpdateManifestUrl,token); });
                if(updatePlan!=null && !PrismBridge.LoaderMatches(prismTarget,updatePlan)) updatePlan.Needed=true;
                try {store.Save(settings);} catch(Exception saveError){store.Log("Prism settings",saveError);}
                UpdateActivity();
                Get<TextBlock>("ConnectionLabel").Text = localTest ? "포켓메이트 멀티플레이" : updatePlan == null ? "서버 업데이트 미연결" : updatePlan.Needed ? "새 업데이트가 있습니다" : "최신 버전입니다";
                Get<TextBlock>("ConnectionDetail").Text = localTest ? "NeoForge · Prism" : updatePlan == null ? "순정 · Prism" : "팩 " + updatePlan.PackVersion;
                Get<TextBlock>("ActionStatus").Text = localTest ? "포켓메이트 서버 · NeoForge 21.1.248" : updatePlan == null ? "순정 Minecraft 1.21.1 · Prism 연결 완료" : updatePlan.Needed ? "업데이트를 누르면 최신 파일을 적용한 뒤 게임 실행을 이어갑니다." : "서버 파일 확인 완료 · Minecraft 1.21.1";
                Get<System.Windows.Shapes.Ellipse>("ConnectionDot").Fill = new SolidColorBrush(updatePlan == null ? Color.FromRgb(176,186,169) : Color.FromRgb(133,202,115));
            }
            catch (OperationCanceledException) { checkError = "업데이트 확인이 취소되었습니다."; Get<TextBlock>("ConnectionLabel").Text = "업데이트 확인 취소"; Get<TextBlock>("ActionStatus").Text = checkError; }
            catch (Exception error) { checkError = error.Message; Get<TextBlock>("ConnectionLabel").Text = "연결/업데이트 확인 실패"; Get<System.Windows.Shapes.Ellipse>("ConnectionDot").Fill = new SolidColorBrush(Color.FromRgb(229,183,99)); Get<TextBlock>("ActionStatus").Text = checkError; store.Log("Update check",error); }
            finally { checking = false; work.Dispose(); work = null; ReadyButton(); if (closingRequested) Window.Close(); }
        }

        async Task OpenGame()
        {
            if(!busy&&!checking&&!PrismInstalled())
            {
                await InstallPrism();
                return;
            }
            if (busy || checking || Get<Grid>("SettingsOverlay").Visibility == Visibility.Visible || Get<Grid>("InfoOverlay").Visibility == Visibility.Visible) return;
            if (gameProcess != null && !gameProcess.HasExited) return;
            if (prismTarget == null) { OpenSettings(); Get<TextBlock>("SettingsError").Text=checkError ?? "Prism 연결 설정을 확인해주세요."; return; }
            if (checkError != null) { await CheckInstallation(); return; }
            busy = true; work = new CancellationTokenSource(); ReadyButton();
            Get<TextBlock>("PlayLabel").Text = updatePlan != null && updatePlan.Needed ? "업데이트 중" : "실행 준비 중";
            IProgress<WorkProgress> progress = new Progress<WorkProgress>(ShowProgress);
            try
            {
                CancellationToken token = work.Token;
                string localTestId = ServerSetting("localTestInstanceId");
                bool packaged = localTestId.Length != 0;
                PrismTarget validated=packaged
                    ? await Task.Run(()=>PrismBridge.EnsureNeoForgeClient(settings,localTestId,ServerSetting("serverAddress")))
                    : await Task.Run(()=>PrismBridge.Resolve(settings));
                if(!String.Equals(validated.Root,(packaged?prismTarget:vanillaTarget).Root,StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Prism 인스턴스 위치가 변경되었습니다. 업데이트를 다시 확인해주세요.");
                Process existing=await Task.Run(()=>PrismBridge.FindGame(vanillaTarget,prismTarget));
                if(existing!=null) {gameProcess=existing;Get<TextBlock>("ActionStatus").Text="연결된 게임이 이미 실행 중입니다.";return;}
                if(packaged)
                {
                    updatePlan = await Task.Run(() => ReadLocalPack(),token);
                    if(updatePlan.Needed)
                        await Task.Run(async delegate { await updates.Apply(updatePlan,progress,token); },token);
                    updatePlan.Needed=false;
                }
                if (localTestId.Length == 0 && !String.IsNullOrWhiteSpace(settings.UpdateManifestUrl))
                {
                    updatePlan = await Task.Run(async delegate { return await updates.Check(settings.UpdateManifestUrl,token); });
                    if (!PrismBridge.LoaderMatches(prismTarget,updatePlan)) updatePlan.Needed=true;
                    if (updatePlan.Needed)
                    {
                        var metadata=new System.Collections.Generic.Dictionary<string,object>{{Path.Combine(prismTarget.Root,"mmc-pack.json"),PrismBridge.LoaderPack(prismTarget,updatePlan)}};
                        await Task.Run(async delegate { await updates.Apply(updatePlan,progress,token,metadata); });
                        updatePlan.Needed=false;Get<TextBlock>("ConnectionLabel").Text="최신 버전입니다";
                    }
                }
                if (prismTarget.Managed && updatePlan != null) await Task.Run(() => updates.VerifyApprovedContent(updatePlan), token);
                token.ThrowIfCancellationRequested();
                gameProcess = await PrismBridge.Start(prismTarget,progress,token,ServerSetting("serverAddress"));
                Json.Save(Path.Combine(store.DirectoryPath,"game-session.json"),new {pid=gameProcess.Id,startTicks=gameProcess.StartTime.ToUniversalTime().Ticks});
                settings.LastOpenedUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture);
                try { store.Save(settings); } catch (Exception error) { store.Log("Activity save", error); }
                UpdateActivity();
                Get<TextBlock>("ActionStatus").Text = "Prism으로 Minecraft Java 1.21.1을 실행했습니다.";
                if (settings.MinimizeAfterLaunch) Window.WindowState = WindowState.Minimized;
            }
            catch (OperationCanceledException) { Get<TextBlock>("ActionStatus").Text = "작업이 취소되었습니다. 다시 게임을 시작할 수 있습니다."; }
            catch (Exception error)
            {
                showPrismLogin=true;
                store.Log("Launch", error);
                Get<TextBlock>("ActionStatus").Text = "작업을 완료하지 못했습니다. 안내를 확인한 뒤 다시 시도해주세요.";
                Info("게임을 시작하지 못했어요", error.Message);
            }
            finally { busy = false; work.Dispose(); work = null; Get<Grid>("WorkArea").Visibility = Visibility.Collapsed; ReadyButton(); if (closingRequested) Window.Close(); }
        }

        void OpenSettings()
        {
            Get<Grid>("InfoOverlay").Visibility = Visibility.Collapsed;
            Get<TextBox>("DisplayNameBox").Text = settings.DisplayName;
            Get<TextBox>("LauncherPathBox").Text = settings.PrismPath ?? "";
            Get<TextBox>("PrismDataBox").Text = settings.PrismDataPath ?? "";
            Get<TextBox>("PrismInstanceBox").Text = settings.PrismInstanceId ?? "";
            Get<TextBox>("UpdateUrlBox").Text = settings.UpdateManifestUrl ?? "";
            Get<TextBox>("BackgroundPathBox").Text = settings.BackgroundPath ?? "";
            Get<CheckBox>("MinimizeAfterLaunchBox").IsChecked = settings.MinimizeAfterLaunch;
            Get<TextBlock>("SettingsError").Text = "";
            Get<Grid>("SettingsOverlay").Visibility = Visibility.Visible;
            Get<TextBox>("DisplayNameBox").Focus();
        }
        void CloseSettings() { Get<Grid>("SettingsOverlay").Visibility = Visibility.Collapsed; }

        async Task SaveSettings()
        {
            try
            {
                string title = Get<TextBox>("DisplayNameBox").Text.Trim();
                string path = Get<TextBox>("LauncherPathBox").Text.Trim().Trim('"');
                string image = Get<TextBox>("BackgroundPathBox").Text.Trim();
                if (title.Length == 0) throw new InvalidOperationException("런처 이름을 입력해주세요.");
                string url = Get<TextBox>("UpdateUrlBox").Text.Trim();
                if (url.Length > 0) Net.Address(url);
                if (image.Length != 0) LoadBitmap(image);
                Settings next = new Settings { DisplayName = title, LauncherPath = path, BackgroundPath = image,
                    MinimizeAfterLaunch = Get<CheckBox>("MinimizeAfterLaunchBox").IsChecked == true,
                    LaunchCount = settings.LaunchCount, LastOpenedUtc = settings.LastOpenedUtc,
                    JavaPath=settings.JavaPath,UpdateManifestUrl=url,MicrosoftClientId=settings.MicrosoftClientId,MemoryMB=settings.MemoryMB,
                    PrismPath=path,PrismDataPath=Get<TextBox>("PrismDataBox").Text.Trim().Trim('"'),PrismInstanceId=Get<TextBox>("PrismInstanceBox").Text.Trim() };
                string testId=ServerSetting("localTestInstanceId");
                if(testId.Length==0)PrismBridge.Resolve(next);
                else PrismBridge.EnsureNeoForgeClient(next,testId,ServerSetting("serverAddress"));
                store.Save(next); settings = next; ApplyAppearance(); CloseSettings();
                Get<TextBlock>("ActionStatus").Text = "설정을 저장했습니다. 다음 실행에도 그대로 적용됩니다.";
                await CheckInstallation();
            }
            catch (Exception error) { Get<TextBlock>("SettingsError").Text = error.Message; }
        }

        void BrowseLauncher()
        {
            OpenFileDialog dialog = new OpenFileDialog { Title = "Prism Launcher 실행 파일 선택", Filter = "Prism Launcher|prismlauncher.exe", CheckFileExists = true };
            if (dialog.ShowDialog(Window) == true) Get<TextBox>("LauncherPathBox").Text = dialog.FileName;
        }
        void BrowseBackground()
        {
            OpenFileDialog dialog = new OpenFileDialog { Title = "배경 이미지 선택", Filter = "이미지 파일|*.png;*.jpg;*.jpeg;*.bmp|모든 파일|*.*", CheckFileExists = true };
            if (dialog.ShowDialog(Window) == true) Get<TextBox>("BackgroundPathBox").Text = dialog.FileName;
        }
        void OpenMinecraftFolder()
        {
            string path;
            try { path=prismTarget!=null ? prismTarget.GameRoot : PrismBridge.Resolve(settings).GameRoot; }
            catch(Exception error){Info("Prism 연결 확인",error.Message);return;}
            Directory.CreateDirectory(path);
            try { Process.Start(new ProcessStartInfo(path) { UseShellExecute = true }); }
            catch (Exception error) { Info("폴더를 열지 못했어요", error.Message); }
        }
        void Info(string title, string body)
        {
            Get<TextBlock>("InfoTitle").Text = title; Get<TextBlock>("InfoBody").Text = body;
            Get<Grid>("InfoOverlay").Visibility = Visibility.Visible;
            Get<Button>("CloseInfoButton").Focus();
        }
        void Render(string path)
        {
            FrameworkElement root = Get<Grid>("Root");
            root.UpdateLayout();
            RenderTargetBitmap bitmap = new RenderTargetBitmap((int)Math.Ceiling(root.ActualWidth), (int)Math.Ceiling(root.ActualHeight), 96, 96, PixelFormats.Pbgra32);
            bitmap.Render(root);
            PngBitmapEncoder encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (FileStream file = File.Create(path)) encoder.Save(file);
            Json.Save(path+".state.json",new{title=Window.Title,button=Get<TextBlock>("PlayLabel").Text,status=Get<TextBlock>("ConnectionLabel").Text,version=GameInstaller.Version,prismInstance=prismTarget==null?null:prismTarget.Id,gameDirectory=prismTarget==null?null:prismTarget.GameRoot,updateRequired=updatePlan!=null&&updatePlan.Needed});
        }
    }

    public static class Program
    {
        public static string Option(string[] args, string option)
        {
            int index = Array.IndexOf(args, option);
            return index >= 0 && index+1 < args.Length ? args[index+1] : null;
        }
        [STAThread]
        public static int Main(string[] args)
        {
            string directory = Option(args, "--data-dir") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SnowfrostLauncher");
            SettingsStore store = new SettingsStore(directory);
            Mutex instance = null; bool ownsInstance = false;
            try
            {
                string key;
                using (System.Security.Cryptography.SHA256 hash=System.Security.Cryptography.SHA256.Create()) key=BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(Path.GetFullPath(directory).ToLowerInvariant()))).Replace("-","").Substring(0,24);
                instance=new Mutex(false,@"Local\Pocketmate-"+key);
                try{ownsInstance=instance.WaitOne(0);}catch(AbandonedMutexException){ownsInstance=true;}
                if(!ownsInstance){MessageBox.Show("같은 게임 폴더를 사용하는 포켓메이트 런처가 이미 실행 중입니다.","포켓메이트 런처");return 2;}
                string backend = Option(args,"--backend-test");
                if (backend != null) { BackendTests.Run(backend,Path.Combine(directory,"test-sandbox"),Option(args,"--fixture-url")).GetAwaiter().GetResult();return 0; }
                string prismTest=Option(args,"--prism-test");
                if(prismTest!=null){BackendTests.PrismLaunch(prismTest,store.Load()).GetAwaiter().GetResult();return 0;}
                string install = Option(args,"--install-test");
                if (install != null) { BackendTests.Install(install,directory).GetAwaiter().GetResult();return 0; }
                string selfTest = Option(args, "--self-test");
                if (selfTest != null) return SelfTest(selfTest);
                Application app = new Application();
                Launcher launcher = new Launcher(store, args);
                app.DispatcherUnhandledException += delegate(object sender, DispatcherUnhandledExceptionEventArgs e) {
                    store.Log("UI", e.Exception); MessageBox.Show(e.Exception.Message, "포켓메이트 런처"); e.Handled = true;
                };
                app.Run(launcher.Window);
                return 0;
            }
            catch (Exception error)
            {
                store.Log("Startup",error);
                string report=Option(args,"--backend-test")??Option(args,"--install-test")??Option(args,"--prism-test")??Option(args,"--self-test");
                if(report!=null) Json.Save(report,new{passed=false,error=error.ToString()});
                else if(Array.IndexOf(args,"--smoke-test")<0 && Option(args,"--render-preview")==null) MessageBox.Show(error.Message,"포켓메이트 런처");
                return 1;
            }
            finally { if(ownsInstance) instance.ReleaseMutex(); if(instance!=null) instance.Dispose(); }
        }

        static int SelfTest(string reportPath)
        {
            string sandbox = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(reportPath)), "settings-test");
            SettingsStore store = new SettingsStore(sandbox);
            int checks = 0;
            Action<bool, string> check = delegate(bool success, string name) { if (!success) throw new Exception("Self test failed: " + name); checks++; };
            Settings defaults = new Settings();
            check(defaults.LaunchCount == 0 && defaults.DisplayName == Settings.DefaultName, "New brand first-run state");
            Settings state = new Settings { DisplayName = "테스트 월드", LaunchCount = 2, LastOpenedUtc = DateTime.UtcNow.ToString("O"), MinimizeAfterLaunch = true };
            store.Save(state); Settings restored = store.Load();
            check(restored.DisplayName == state.DisplayName && restored.MinimizeAfterLaunch && restored.LaunchCount == 2, "Unicode and activity persistence");
            state.LaunchCount = 3; store.Save(state); check(store.Load().LaunchCount == 3, "Atomic settings update");
            Settings legacy = new Settings { DisplayName = "나무온라인", LaunchCount = 7, LauncherPath = "legacy.exe", MinimizeAfterLaunch = true };
            store.Save(legacy); Settings migrated = store.Load();
            check(migrated.DisplayName == Settings.DefaultName && migrated.LaunchCount == 7 && migrated.LauncherPath == "legacy.exe" && migrated.MinimizeAfterLaunch, "Legacy brand migration preserves settings");
            check(new JavaScriptSerializer().Deserialize<Settings>(File.ReadAllText(Path.Combine(sandbox, "settings.json"), Encoding.UTF8)).DisplayName == Settings.DefaultName, "Brand migration is persisted");
            check(GameInstaller.SelectLoader(false, Tuple.Create("fabric", "0.16.14")).Item1 == "vanilla", "No server overrides previous Fabric loader");
            check(GameInstaller.Version == "1.21.1", "Vanilla version pinned to 1.21.1");
            var report = new { passed = true, checks = checks, actualLaunchExecuted = false, accountFilesRead = false,
                backgroundBundled = Assembly.GetExecutingAssembly().GetManifestResourceStream("Snowfrost.Background.png") != null };
            File.WriteAllText(reportPath, new JavaScriptSerializer().Serialize(report), new UTF8Encoding(false));
            return 0;
        }
    }
}
