const McConfig = {
    // development | production
    nodeEnv:'development',
    env: {
        production: {
            baseApiURL: 'https://fcloud.tqclink.cn:5000',
        },
        development: {
            baseApiURL: 'http://localhost:5000',
        },
    },
    server: {
        id: 1,
        address: 'play.simpfun.cn',
        port: 37298,
        // id: 3,
        // address: 'h1.getmc.cn',
        // port: 39030,
        supportedVersions: {
            java: '1.18 - 1.21.11',
            bedrock: '1.18.100 - 1.21.200'
        }
    },
    qqGroup: {
        id: 942235691,
        codeImgUrl: "https://img.fastmirror.net/s/2025/11/30/692bdccb7daa6.jpg",
        inviteLinkUrl: "https://qm.qq.com/q/8jQDx8OCOY"
    }
}

export default McConfig