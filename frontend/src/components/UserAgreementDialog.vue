<template>
  <Modal
    :is-visible="visible"
    title="星穹旅驿用户协议"
    date="最近修订：2025-10-11 · 摘编自官方 Wiki「服务器条例」分区"
    @close="$emit('close')"
  >
    <div class="ua-body">
      <p class="ua-intro">
        欢迎来到星穹旅驿《Minecraft》服务器！在注册账号、进入服务器或提交内测申请前，请仔细阅读本协议。勾选同意即表示你已理解并接受以下全部内容。
      </p>

      <h4>一、总则</h4>
      <ul>
        <li>本协议适用于星穹旅驿游戏服务端及其附属 QQ 群、交流平台；<strong>进入服务器即视为同意并接受全部约束</strong>。</li>
        <li>《服务器法典》为本服务器最高行为准则，本协议为其摘要；如与 Wiki 原文不一致，以 Wiki 原文为准。</li>
        <li>服主拥有本协议及服务器一切事务的最终解释权与最高决策权；协议修订将在社群内公示后生效。</li>
      </ul>

      <h4>二、账号与虚拟财产</h4>
      <ul>
        <li>请妥善保管账号密码，谨防诈骗；因账号主动泄露造成的损失原则上由玩家自行承担。</li>
        <li>游戏内货币、物品、装备、建筑、红石机械、驯养生物等均属玩家虚拟财产。</li>
        <li><strong>责任原则：请保护好自己的资产</strong>——使用领地插件圈地、上锁箱子；因自身未加保护导致的物品被偷或建筑被破坏，管理团队原则上不予处理。</li>
        <li>玩家间交易请自行甄别风险，建议留存截图 / 视频作为证据；遭遇欺诈请立即带证据私聊管理员举报。</li>
      </ul>

      <h4>三、行为规范</h4>
      <ul>
        <li><strong>公平原则：</strong>禁止任何形式的外挂、作弊客户端与不公平竞争——包括但不限于透视、飞行、杀戮光环、自动挖掘、X-Ray、利用 BUG 复制刷取物品牟利。此类重罪一经发现<strong>永久封禁全部相关账户并清空物资</strong>，并在服务器及 QQ 群内公示。</li>
        <li><strong>尊重原则：</strong>禁止恶意破坏（Griefing）他人建筑、地形与装置，首犯即永久封禁并尽可能回滚；禁止发表仇恨、歧视、淫秽、暴力恐怖及其他违反法律法规的言论；禁止人身攻击、辱骂与故意引战。</li>
        <li><strong>诚信原则：</strong>禁止欺诈、盗窃与背信行为；轻度失信需归还财物并公开道歉，严重欺诈将永久封禁。</li>
        <li><strong>秩序规范：</strong>禁止刷屏、垃圾信息与第三方广告（禁言 1 小时 → 24 小时 → 永久禁言）；禁止高频红石、大量繁殖生物等导致服务器卡顿的行为；未经许可不得占用公共区域建造，逾期未拆除将被强制清除且不予补偿。</li>
      </ul>

      <h4>四、处罚与申诉</h4>
      <ul>
        <li>处罚分级：重罪永久封禁并清空资产；轻罪按「警告 → 短期封禁 1-7 天 → 永久封禁」阶梯处罚并追回非法所得；过失以警告、教育、恢复原状为主。</li>
        <li>执行处罚时会明确告知违规事实、依据条款、处罚时限与申诉渠道。</li>
        <li>若认为处罚有误，可在收到处罚后 <strong>72 小时内</strong>通过 QQ 私聊在线管理员申诉，说明游戏 ID、时间、理由并附上证据；确属误判将立即解除处罚、公开道歉并恢复资产。</li>
        <li>举报遵循「谁主张，谁举证」；捏造事实、恶意投诉者将受到处罚；同一事件无新证据的重复申诉不再受理。</li>
      </ul>

      <h4>五、内测相关</h4>
      <ul>
        <li>内测玩法处于开发阶段，玩法内容、规则与地图数据可能随时调整或回档，请知悉并理解。</li>
        <li>内测期间同样适用本协议全部规范；欢迎积极反馈问题，共同完善玩法。</li>
      </ul>

      <h4>六、附则</h4>
      <ul>
        <li>本协议任何条款与中华人民共和国法律法规相抵触的，以国家法律法规为准。</li>
        <li>服务器承诺财务公开透明、坚持每日自动备份（极端情况下最多可能损失 24 小时数据）。</li>
        <li>本协议的修改权与最终解释权归服主所有。</li>
      </ul>

      <p class="ua-footnote">
        完整细则请阅读官方 Wiki 的《服务器法典》《服务器游玩规则与惩罚条例》《玩家维权与投诉处理条例》。
      </p>

      <div class="ua-actions">
        <button type="button" class="ua-btn-primary" @click="$emit('agree')">我已阅读并同意</button>
        <button type="button" class="ua-btn-ghost" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </Modal>
</template>

<script>
import Modal from "./Modal.vue";

export default {
  name: "UserAgreementDialog",
  components: { Modal },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["close", "agree"],
};
</script>

<style scoped>
.ua-body {
  text-align: left;
}

.ua-intro {
  font-size: 14px;
  color: var(--text-color);
  line-height: 1.8;
  margin: 0 0 14px;
  padding: 10px 12px;
  background-color: #fafafa;
  border: 2px solid var(--border-color);
}

.ua-body h4 {
  font-size: 15px;
  color: var(--primary-color);
  margin: 16px 0 8px;
  padding-left: 8px;
  border-left: 4px solid var(--primary-color);
}

.ua-body ul {
  margin: 0;
  padding-left: 20px;
}

.ua-body li {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
  margin-bottom: 6px;
}

.ua-body li strong {
  color: var(--text-color);
}

.ua-footnote {
  font-size: 12px;
  color: #888;
  line-height: 1.7;
  margin: 16px 0 0;
  padding-top: 10px;
  border-top: 2px dashed var(--border-color);
}

.ua-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 18px;
}

.ua-btn-primary,
.ua-btn-ghost {
  padding: 9px 22px;
  font-size: 14px;
  font-weight: bold;
  font-family: inherit;
  cursor: pointer;
  border: 3px solid var(--border-color);
}

.ua-btn-primary {
  background-color: var(--primary-color);
  color: #fff;
}

.ua-btn-primary:hover {
  filter: brightness(1.08);
}

.ua-btn-ghost {
  background-color: #fff;
  color: var(--text-color);
}

.ua-btn-ghost:hover {
  background-color: #f0f0f0;
}
</style>
