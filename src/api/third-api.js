import axios from 'axios';


export const getServerStatus = (address) => {
    // 将address按冒号分割，获取IP和端口
    const [ip, port=''] = address.split(':');
    // 构建API请求URL
    const apiUrl = `https://motd.minebbs.com/api/status?ip=${ip}&port=${port}`;
    // 发送GET请求并返回Promise
    return axios.get(apiUrl);
}