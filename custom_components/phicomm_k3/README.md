# Phicomm K3 Home Assistant设备追踪插件

这个Home Assistant自定义组件允许您通过SSH追踪连接到Phicomm K3路由器的设备。

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

## 兼容性

此插件专为使用[此链接](https://tbvv.net/posts/0101-k3)提供的固件刷写的Phicomm K3路由器而设计。如果您之前刷写了Merlin固件，则建议在安装此插件之前先刷写LEDE。直接刷写官方root固件可能会导致分区格式错误。

## 安装

### 通过HACS安装（推荐）

1. 打开Home Assistant的HACS（Home Assistant Community Store）插件。
2. 进入“集成”页面，点击右上角的三个点，选择“仓库”。
3. 在“仓库URL”中添加：`https://github.com/KaiShaoHoi/phicomm_k3`。
4. 点击“添加”，然后在搜索框中搜索插件：`phicomm_k3`。
5. 点击搜索结果中的插件，然后点击“安装”。

### 手动安装

1. 下载插件文件并解压。
2. 将解压后的文件夹复制到Home Assistant的custom components目录下：

    ```
    .homeassistant/custom_components/phicomm_k3
    ```

3. 通常情况下，所需的依赖项会自动安装。如果没有，请使用以下命令手动安装：

    ```bash
    sudo su -s /bin/bash homeassistant
    source /srv/homeassistant/bin/activate
    pip3 install paramiko -i http://pypi.douban.com/simple --trusted-host pypi.douban.com
    pip install pexpect
    ```

4. 如果在paramiko安装过程中遇到错误，请退出虚拟环境并安装所需的依赖项：

    ```bash
    sudo apt-get install libffi-dev libssl-dev
    ```

## 配置

在Home Assistant的`configuration.yaml`文件中添加以下配置：

```yaml
device_tracker:
  - platform: phicomm_k3
    host: 192.168.1.1
    protocol: ssh
    username: admin
    password: YOUR_ROUTER_PASSWORD
    interval_seconds: 3
    consider_home: 3
    track_new_devices: yes
```

确保将`YOUR_ROUTER_PASSWORD`替换为路由器的实际密码。

## 工作原理

插件通过SSH连接到路由器并执行以下命令以检索关联设备列表：

```bash
wl -i eth1 assoclist;wl -i eth2 assoclist;cat /proc/net/arp | awk '{if(NR>1) print $4}'
```

然后，插件返回在线设备的MAC地址。

## 已知问题

1. 插件目前没有通过SSH高效获取设备名称的方法。因此，device_tracker返回的名称是不带冒号的MAC地址。您可以在`known_devices.yaml`文件中手动设置所需的名称和图片。

2. 当设备离开Wi-Fi网络时，device_tracker的状态从'Home'变为'Away'，延迟大约为2到3分钟。

如果您对上述问题有解决方案，请随时提出问题。
