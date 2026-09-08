// 站点配置统一读取层：全部取值来自 Vite 环境变量（frontend/.env / .env.development / .env.production，
// 本地覆盖写 .env.local），各变量的含义与默认值见 env 文件内注释。
// 规约：不要在本文件硬编码站点值，也不要在组件里直接读 import.meta.env —— 一律从本模块取。
const env = import.meta.env

const McConfig = {
    // API 基础地址：dev 默认 http://localhost:5000（.env.development），
    // 生产默认 ''（同源相对路径，由 Nginx 反代到本机 FastAPI）
    baseApiURL: env.VITE_BASE_API_URL ?? '',
    server: {
        // 监控接口的路由参数（与后端 SERVERS 注册表的主服务器 id 对应）
        id: Number(env.VITE_SERVER_ID),
        supportedVersions: {
            java: env.VITE_JAVA_VERSIONS,
            bedrock: env.VITE_BEDROCK_VERSIONS,
        },
    },
    qqGroup: {
        id: Number(env.VITE_QQ_GROUP_ID),
        codeImgUrl: env.VITE_QQ_GROUP_CODE_IMG_URL,
        inviteLinkUrl: env.VITE_QQ_GROUP_INVITE_LINK_URL,
    },
    // 后台管理入口：相对路径或绝对路径，默认 /admin（独立后台管理前端）
    adminUrl: env.VITE_ADMIN_URL,
    // Wiki 入口：相对路径或绝对路径，默认 /wiki/（VitePress 构建产物）；
    // 开发模式由 .env.development 覆盖为本地 VitePress dev server 绝对地址
    wikiUrl: env.VITE_WIKI_URL,
}

export default McConfig
