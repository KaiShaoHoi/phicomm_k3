# Phicomm K3 Home Assistant设备追踪插件

这个Home Assistant自定义组件允许您通过Web API追踪连接到Phicomm K3路由器的设备。

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
    pip3 install requests
    ```

## 配置

在Home Assistant的`configuration.yaml`文件中添加以下配置：

```yaml
device_tracker:
  - platform: phicomm_k3
    host: 192.168.1.1
    username: admin
    password: YOUR_ROUTER_PASSWORD
    interval_seconds: 3
    consider_home: 3
    track_new_devices: yes
```

确保将`YOUR_ROUTER_PASSWORD`替换为路由器的实际密码。

## 工作原理

插件通过HTTP请求连接到路由器的Web管理界面，使用以下步骤获取设备信息：

1. 首先通过POST请求到 `/cgi-bin/` 端点进行身份验证，获取访问令牌(stok)
2. 使用获取的令牌向 `/cgi-bin/stok={token}/data` 端点发送请求，获取客户端设备列表
3. 解析返回的JSON数据，提取在线设备的MAC地址和设备名称

插件现在能够直接从路由器的Web API获取设备名称，无需手动配置。

## 功能特性

- **自动设备名称识别**：插件现在可以直接从路由器的Web API获取设备的真实名称，无需手动在`known_devices.yaml`中配置
- **实时状态更新**：通过Web API实时获取设备在线状态
- **简化配置**：不再需要SSH连接，只需提供Web管理界面的用户名和密码

## 已知问题

1. 当设备离开Wi-Fi网络时，device_tracker的状态从'Home'变为'Away'，延迟大约为2到3分钟。

2. 需要确保路由器的Web管理界面可访问，并且提供的用户名和密码正确。

如果您遇到任何问题或有改进建议，请随时提出issue。
