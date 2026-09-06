const McConfig = {
    // 根据构建模式自动切换：vite dev → development（本地 FastAPI），vite build → production（同源）
    nodeEnv: import.meta.env.PROD ? 'production' : 'development',
    env: {
        production: {
            // 前后端同域部署：API 走同源相对路径，由 nginx 反代到本机 FastAPI
            baseApiURL: '',
        },
        development: {
            baseApiURL: 'http://localhost:5000',
        },
    },
    server: {
        // 游戏服务器地址已改为由后端 /monitor/servers 统一维护（单一数据源）；
        // id 是监控接口的路由参数（与后端 SERVERS 的主服务器 id 对应）
        id: 1,
        supportedVersions: {
            java: '1.18 - 1.21.11',
            bedrock: '1.18.100 - 1.21.200'
        }
    },
    qqGroup: {
        id: 942235691,
        codeImgUrl: "https://img.fastmirror.net/s/2025/11/30/692bdccb7daa6.jpg",
        inviteLinkUrl: "https://qm.qq.com/q/8jQDx8OCOY"
    },
    // 后台管理入口：相对路径或绝对路径，默认 /admin（独立后台管理前端）
    adminUrl: '/admin'
}

export default McConfig