"""
广告管理系统
- 广告主注册
- 创建广告计划（关键词+频道+预算）
- 搜索时插入广告位
- 按曝光/点击扣费
- 广告模板库
"""
from datetime import datetime, date
from loguru import logger
from app.database import get_db
from app.wallet.wallet_manager import wallet_manager


class AdManager:
    """广告管理"""

    async def become_advertiser(self, tg_user_id: int) -> dict:
        """用户成为广告主"""
        user = await wallet_manager.get_or_create_user(tg_user_id)

        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM advertisers WHERE user_id=?", (user["id"],))
            existing = await cursor.fetchone()
            if existing:
                return dict(existing)

            await db.execute(
                "INSERT INTO advertisers (user_id, status) VALUES (?, 'active')",
                (user["id"],),
            )
            # 同时更新用户角色
            await db.execute("UPDATE users SET role='advertiser' WHERE id=?", (user["id"],))
            await db.commit()

        logger.info(f"用户 {tg_user_id} 成为广告主")
        return {"user_id": user["id"], "status": "active"}

    async def create_campaign(self, tg_user_id: int, campaign_data: dict) -> dict:
        """
        创建广告计划
        campaign_data: {
            keyword, title, description, target_channel, target_url,
            category, member_count,
            billing_type, cpc_price, cpm_price, daily_budget
        }
        """
        user = await wallet_manager.get_or_create_user(tg_user_id)

        # 获取广告主ID
        async with get_db() as db:
            cursor = await db.execute("SELECT id FROM advertisers WHERE user_id=?", (user["id"],))
            advertiser = await cursor.fetchone()
            if not advertiser:
                return {"success": False, "error": "请先成为广告主"}

            advertiser = dict(advertiser)

            # 检查余额（至少要有1U才能创建广告）
            if user["wallet_balance_usdt"] < 1.0:
                return {"success": False, "error": "余额不足，请先充值", "balance": user["wallet_balance_usdt"]}

            cursor = await db.execute(
                """INSERT INTO ad_campaigns
                (advertiser_id, keyword, title, description, target_channel, target_url,
                 category, member_count,
                 billing_type, cpc_price, cpm_price, daily_budget, daily_spent, status, start_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,'active',?)""",
                (
                    advertiser["id"],
                    campaign_data["keyword"],
                    campaign_data.get("title", ""),
                    campaign_data.get("description", ""),
                    campaign_data.get("target_channel", ""),
                    campaign_data.get("target_url", ""),
                    campaign_data.get("category", "推广"),
                    campaign_data.get("member_count", 10000),
                    campaign_data.get("billing_type", "cpc"),
                    campaign_data.get("cpc_price", 0.05),
                    campaign_data.get("cpm_price", 1.0),
                    campaign_data.get("daily_budget", 10.0),
                    datetime.now(),
                ),
            )
            await db.commit()
            campaign_id = cursor.lastrowid

        logger.info(f"广告计划创建: ID={campaign_id} 关键词={campaign_data['keyword']}")
        return {"success": True, "campaign_id": campaign_id}

    async def _check_and_pause_exhausted(self) -> int:
        """
        检查所有 active 广告：
        - 每日预算耗尽（daily_spent >= daily_budget）
        - 或广告主钱包余额为0（无法再扣费）
        自动改为 paused 状态。
        返回被暂停的广告数量。
        """
        paused_count = 0
        try:
            async with get_db() as db:
                # 1. 找出所有 active 广告
                cursor = await db.execute(
                    """SELECT ac.id, ac.daily_spent, ac.daily_budget, u.tg_user_id
                       FROM ad_campaigns ac
                       JOIN advertisers adv ON adv.id = ac.advertiser_id
                       JOIN users u ON u.id = adv.user_id
                       WHERE ac.status='active'"""
                )
                rows = [dict(r) for r in await cursor.fetchall()]
                for r in rows:
                    reason = None
                    # 日预算耗尽
                    if (r.get("daily_spent") or 0) >= (r.get("daily_budget") or 0):
                        reason = "daily_budget_exhausted"
                    else:
                        # 钱包余额不足（低于安全阈值0.01U，无法再扣费）
                        bal = await wallet_manager.get_balance(r["tg_user_id"])
                        if bal < 0.01:
                            reason = "wallet_empty"
                    if reason:
                        await db.execute(
                            "UPDATE ad_campaigns SET status='paused' WHERE id=?",
                            (r["id"],),
                        )
                        paused_count += 1
                        logger.info(f"自动暂停广告 #{r['id']} 原因={reason} tg_user={r['tg_user_id']}")
                if paused_count:
                    await db.commit()
        except Exception as e:
            logger.error(f"_check_and_pause_exhausted 错误: {e}")
        return paused_count

    async def get_featured_ads(self, limit: int = 3) -> list:
        """获取首页推荐广告（按 display_order 排序，is_featured 优先）"""
        # 先自动暂停耗尽预算或余额不足的广告
        await self._check_and_pause_exhausted()
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT ac.*, adv.user_id
                   FROM ad_campaigns ac
                   JOIN advertisers adv ON adv.id = ac.advertiser_id
                   WHERE ac.status='active' AND ac.daily_spent < ac.daily_budget
                   ORDER BY ac.is_featured DESC, ac.display_order ASC, ac.id ASC
                   LIMIT ?""",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_featured_channels(self, limit: int = 10) -> list:
        """获取置顶推广频道列表（与Web演示页保持一致，查询channels表is_featured=1）"""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT * FROM channels
                   WHERE is_featured = 1
                   ORDER BY sort_order ASC, id ASC
                   LIMIT ?""",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_hot_keywords(self, limit: int = 8, category: str = None) -> list:
        """获取热门搜索关键词（优先后台配置的，再补系统默认的）"""
        async with get_db() as db:
            if category:
                cursor = await db.execute(
                    """SELECT * FROM hot_keywords
                       WHERE is_active=1 AND category=?
                       ORDER BY display_order ASC, id ASC
                       LIMIT ?""",
                    (category, limit)
                )
            else:
                cursor = await db.execute(
                    """SELECT * FROM hot_keywords
                       WHERE is_active=1
                       ORDER BY is_custom DESC, display_order ASC, id ASC
                       LIMIT ?""",
                    (limit,)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_hot_keywords_by_category(self) -> dict:
        """按分类获取所有热门关键词"""
        async with get_db() as db:
            # 获取所有启用的分类
            cat_cursor = await db.execute(
                "SELECT * FROM hot_keyword_categories WHERE is_active=1 ORDER BY sort_order ASC"
            )
            categories = [dict(row) for row in await cat_cursor.fetchall()]
            
            result = {}
            for cat in categories:
                kw_cursor = await db.execute(
                    """SELECT * FROM hot_keywords
                       WHERE is_active=1 AND category=?
                       ORDER BY display_order ASC, id ASC""",
                    (cat["name"],)
                )
                keywords = [dict(row) for row in await kw_cursor.fetchall()]
                if keywords:
                    result[cat["name"]] = {
                        "icon": cat["icon"],
                        "keywords": keywords
                    }
            return result

    async def add_hot_keyword(self, keyword: str, category: str = None, display_order: int = 0) -> dict:
        """添加自定义热门关键词"""
        try:
            async with get_db() as db:
                await db.execute(
                    """INSERT OR IGNORE INTO hot_keywords (keyword, category, display_order, is_custom, is_active)
                       VALUES (?,?,?,1,1)""",
                    (keyword, category, display_order)
                )
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_hot_keyword(self, keyword_id: int, **kwargs) -> dict:
        """更新热门关键词"""
        try:
            allowed_fields = {"keyword", "category", "display_order", "is_active"}
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            if not updates:
                return {"success": False, "error": "无更新字段"}
            
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [keyword_id]
            
            async with get_db() as db:
                await db.execute(
                    f"UPDATE hot_keywords SET {set_clause} WHERE id=?",
                    values
                )
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_hot_keyword(self, keyword_id: int) -> dict:
        """删除热门关键词（仅允许删除自定义的，系统默认的软删除）"""
        try:
            async with get_db() as db:
                # 检查是否为系统默认
                cursor = await db.execute("SELECT is_custom FROM hot_keywords WHERE id=?", (keyword_id,))
                row = await cursor.fetchone()
                if row and row["is_custom"] == 0:
                    # 系统默认：软删除（禁用）
                    await db.execute("UPDATE hot_keywords SET is_active=0 WHERE id=?", (keyword_id,))
                else:
                    # 自定义：硬删除
                    await db.execute("DELETE FROM hot_keywords WHERE id=?", (keyword_id,))
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_hot_keywords(self, category: str = None) -> list:
        """列出热门关键词（管理用）"""
        async with get_db() as db:
            if category:
                cursor = await db.execute(
                    "SELECT * FROM hot_keywords WHERE category=? ORDER BY is_custom DESC, display_order ASC, id ASC",
                    (category,)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM hot_keywords ORDER BY category, is_custom DESC, display_order ASC, id ASC"
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def list_keyword_categories(self) -> list:
        """列出所有关键词分类"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM hot_keyword_categories WHERE is_active=1 ORDER BY sort_order ASC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_campaign_order(self, campaign_id: int, display_order: int = None, is_featured: bool = None) -> dict:
        """更新广告的展示顺序和首页推荐状态"""
        try:
            updates = []
            values = []
            if display_order is not None:
                updates.append("display_order=?")
                values.append(display_order)
            if is_featured is not None:
                updates.append("is_featured=?")
                values.append(1 if is_featured else 0)
            
            if not updates:
                return {"success": False, "error": "无更新字段"}
            
            values.append(campaign_id)
            async with get_db() as db:
                await db.execute(
                    f"UPDATE ad_campaigns SET {', '.join(updates)} WHERE id=?",
                    values
                )
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_campaign_status(self, campaign_id: int, status: str) -> dict:
        """暂停/启用广告：status ∈ {active, paused, ended}"""
        allowed = {"active", "paused", "ended", "pending"}
        if status not in allowed:
            return {"success": False, "error": f"无效状态: {status}"}
        try:
            async with get_db() as db:
                await db.execute(
                    "UPDATE ad_campaigns SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (status, campaign_id),
                )
                await db.commit()
            logger.info(f"广告 #{campaign_id} 状态变更为 {status}")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_campaign(self, campaign_id: int) -> dict:
        """删除广告计划（同步删除曝光记录，避免外键残留）"""
        try:
            async with get_db() as db:
                await db.execute("DELETE FROM ad_impressions WHERE campaign_id=?", (campaign_id,))
                await db.execute("DELETE FROM ad_campaigns WHERE id=?", (campaign_id,))
                await db.commit()
            logger.info(f"广告 #{campaign_id} 已删除")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_campaign(self, campaign_id: int, **fields) -> dict:
        """编辑广告字段：支持 keyword, title, description, target_channel, target_url,
        category, member_count, billing_type, cpc_price, cpm_price, daily_budget,
        display_order, is_featured"""
        allowed = {"keyword", "title", "description", "target_channel", "target_url",
                   "category", "member_count", "billing_type", "cpc_price", "cpm_price",
                   "daily_budget", "display_order", "is_featured"}
        updates = []
        values = []
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "is_featured":
                v = 1 if v else 0
            updates.append(f"{k}=?")
            values.append(v)
        if not updates:
            return {"success": False, "error": "无有效更新字段"}
        # 自动更新 updated_at
        updates.append("updated_at=CURRENT_TIMESTAMP")
        values.append(campaign_id)
        try:
            async with get_db() as db:
                await db.execute(
                    f"UPDATE ad_campaigns SET {', '.join(updates)} WHERE id=?",
                    values,
                )
                await db.commit()
            logger.info(f"广告 #{campaign_id} 更新: {list(fields.keys())}")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def add_keyword_category(self, name: str, icon: str = "📌", sort_order: int = 0) -> dict:
        """添加关键词分类"""
        try:
            async with get_db() as db:
                await db.execute(
                    "INSERT INTO hot_keyword_categories (name, icon, sort_order, is_active) VALUES (?,?,?,1)",
                    (name, icon, sort_order)
                )
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_keyword_category(self, category_id: int, name: str = None, icon: str = None, sort_order: int = None, is_active: bool = None) -> dict:
        """更新关键词分类"""
        try:
            updates = []
            values = []
            if name is not None:
                updates.append("name=?")
                values.append(name)
            if icon is not None:
                updates.append("icon=?")
                values.append(icon)
            if sort_order is not None:
                updates.append("sort_order=?")
                values.append(sort_order)
            if is_active is not None:
                updates.append("is_active=?")
                values.append(1 if is_active else 0)
            
            if not updates:
                return {"success": False, "error": "无更新字段"}
            
            values.append(category_id)
            async with get_db() as db:
                await db.execute(
                    f"UPDATE hot_keyword_categories SET {', '.join(updates)} WHERE id=?",
                    values
                )
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_keyword_category(self, category_id: int) -> dict:
        """删除关键词分类（软删除）"""
        try:
            async with get_db() as db:
                await db.execute(
                    "UPDATE hot_keyword_categories SET is_active=0 WHERE id=?",
                    (category_id,)
                )
                # 同时将该分类下的关键词也设为不活跃
                await db.execute(
                    "UPDATE hot_keywords SET is_active=0 WHERE category=(SELECT name FROM hot_keyword_categories WHERE id=?)",
                    (category_id,)
                )
                await db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_ads_for_keyword(self, keyword: str, limit: int = 3) -> list:
        """
        根据搜索关键词获取匹配的广告
        广告位插入搜索结果头部
        """
        # 先自动暂停耗尽预算或余额不足的广告
        await self._check_and_pause_exhausted()
        async with get_db() as db:
            # 精确匹配关键词的广告 + 模糊匹配
            cursor = await db.execute(
                """
                SELECT ac.*, adv.user_id
                FROM ad_campaigns ac
                JOIN advertisers adv ON adv.id = ac.advertiser_id
                WHERE ac.status='active'
                  AND ac.daily_spent < ac.daily_budget
                  AND (ac.keyword = ? OR ac.keyword LIKE ?)
                ORDER BY
                    CASE WHEN ac.keyword = ? THEN 0 ELSE 1 END,
                    ac.cpc_price DESC,
                    ac.updated_at DESC
                LIMIT ?
                """,
                (keyword, f"%{keyword}%", keyword, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def record_impression(
        self,
        campaign_id: int,
        searcher_tg_id: int,
        is_click: bool = False,
        position: int = 1,
    ) -> dict:
        """
        记录广告曝光/点击，并扣费
        返回: {success, cost, balance_after}
        """
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM ad_campaigns WHERE id=?", (campaign_id,))
            campaign = await cursor.fetchone()
            if not campaign:
                return {"success": False, "error": "广告不存在"}

            campaign = dict(campaign)

            # 计算费用
            if campaign["billing_type"] == "cpc":
                if not is_click:
                    # CPC模式下曝光不扣费
                    cost = 0.0
                else:
                    cost = campaign["cpc_price"]
            else:  # cpm
                cost = campaign["cpm_price"] / 1000.0

            # 检查日预算
            if campaign["daily_spent"] + cost > campaign["daily_budget"]:
                return {"success": False, "error": "已达日预算上限"}

            # 记录曝光
            await db.execute(
                """INSERT INTO ad_impressions (campaign_id, searcher_tg_id, position, is_click, cost)
                VALUES (?,?,?,?,?)""",
                (campaign_id, searcher_tg_id, position, 1 if is_click else 0, cost),
            )

            # 更新广告已花费
            await db.execute(
                "UPDATE ad_campaigns SET daily_spent = daily_spent + ? WHERE id=?",
                (cost, campaign_id),
            )
            await db.commit()

        # 扣减广告主余额
        if cost > 0:
            # 查找广告主的TG ID
            async with get_db() as db:
                cursor = await db.execute(
                    """SELECT u.tg_user_id FROM users u
                    JOIN advertisers adv ON adv.user_id = u.id
                    JOIN ad_campaigns ac ON ac.advertiser_id = adv.id
                    WHERE ac.id=?""",
                    (campaign_id,),
                )
                row = await cursor.fetchone()
                if row:
                    result = await wallet_manager.deduct_balance(
                        row["tg_user_id"],
                        cost,
                        "ad_charge",
                        f"广告扣费({'点击' if is_click else '曝光'}) 计划ID={campaign_id}",
                        campaign_id,
                    )
                    return {"success": True, "cost": cost, "balance_after": result.get("balance_after")}

        return {"success": True, "cost": cost}

    async def list_campaigns(self, tg_user_id: int) -> list:
        """列出广告主的所有广告计划"""
        user = await wallet_manager.get_or_create_user(tg_user_id)
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT ac.* FROM ad_campaigns ac
                JOIN advertisers adv ON adv.id = ac.advertiser_id
                WHERE adv.user_id=?
                ORDER BY ac.created_at DESC""",
                (user["id"],),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_campaign_stats(self, campaign_id: int) -> dict:
        """获取广告计划统计数据"""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT
                    COUNT(*) as total_impressions,
                    SUM(CASE WHEN is_click=1 THEN 1 ELSE 0 END) as total_clicks,
                    SUM(cost) as total_cost
                FROM ad_impressions WHERE campaign_id=?""",
                (campaign_id,),
            )
            row = await cursor.fetchone()
            if row:
                stats = dict(row)
                stats["ctr"] = (
                    (stats["total_clicks"] / stats["total_impressions"] * 100)
                    if stats["total_impressions"] and stats["total_impressions"] > 0
                    else 0.0
                )
                return stats
            return {"total_impressions": 0, "total_clicks": 0, "total_cost": 0.0, "ctr": 0.0}

    async def init_templates(self):
        """初始化广告模板库"""
        templates = [
            {
                "name": "频道推广-标准",
                "category": "频道推广",
                "title_template": "📣 {频道名称} - {频道定位}",
                "desc_template": "专注{领域}内容，{成员数}人已加入",
                "example_text": "📣 加密货币资讯 - 专注区块链行业动态\n50000+成员已加入，每日推送最新资讯",
                "is_recommended": 1,
            },
            {
                "name": "产品推广-直接",
                "category": "产品推广",
                "title_template": "🔥 {产品名称} - {核心卖点}",
                "desc_template": "{功能描述}，立即体验→{链接}",
                "example_text": "🔥 TG搜索Pro - 全网最快搜索\n支持关键词/频道/消息搜索，立即体验→@search_pro_bot",
                "is_recommended": 1,
            },
            {
                "name": "活动推广-空投",
                "category": "活动推广",
                "title_template": "🎁 {活动名称} 空投进行中",
                "desc_template": "参与{任务}即得{奖励}，截止{日期}",
                "example_text": "🎁 TG搜索平台首发空投\n关注+转发即得10U奖励，截止本月底",
                "is_recommended": 1,
            },
        ]

        async with get_db() as db:
            for tpl in templates:
                await db.execute(
                    """INSERT OR IGNORE INTO ad_templates
                    (name, category, title_template, desc_template, example_text, is_recommended)
                    VALUES (?,?,?,?,?,?)""",
                    (
                        tpl["name"],
                        tpl["category"],
                        tpl["title_template"],
                        tpl["desc_template"],
                        tpl["example_text"],
                        tpl["is_recommended"],
                    ),
                )
            await db.commit()
        logger.info(f"初始化 {len(templates)} 个广告模板")

    async def list_templates(self, category: str = None) -> list:
        """获取广告模板列表"""
        async with get_db() as db:
            if category:
                cursor = await db.execute(
                    "SELECT * FROM ad_templates WHERE category=? ORDER BY is_recommended DESC",
                    (category,),
                )
            else:
                cursor = await db.execute("SELECT * FROM ad_templates ORDER BY is_recommended DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ---------------------------------------------------------------------
    # 以下方法给搜索流程 / 演示服务调用（统一的广告服务接口）
    # ---------------------------------------------------------------------
    async def serve_ad_for_keyword(self, keyword: str, searcher_tg_id: int, position: int = 1) -> dict:
        """
        搜索时调用：找到匹配广告 + 记录一条曝光（CPC曝光不扣钱，点击才扣；CPM曝光直接扣）
        返回: {"campaign": {...campaign+remaining_budget}, "impression_id": int, "cost": float}
        或 None（无匹配广告/预算不足）
        """
        # 1. 匹配广告
        ads = await self.get_ads_for_keyword(keyword, limit=1)
        if not ads:
            return None
        ad = ads[0]

        # 2. 记录曝光（CPM会直接扣曝光费，CPC此时曝光不扣费等点击才扣）
        imp_result = await self.record_impression(
            campaign_id=ad["id"],
            searcher_tg_id=searcher_tg_id,
            is_click=False,  # 先记曝光，用户点了再单独track_click
            position=position,
        )
        imp_id = None
        if imp_result.get("success"):
            async with get_db() as db:
                cur = await db.execute(
                    "SELECT last_insert_rowid() AS id FROM ad_impressions LIMIT 1"
                )
                r = await cur.fetchone()
                imp_id = r["id"] if r else None

        # 3. 算出剩余预算（广告卡片展示用）
        remaining_budget = max(0.0, (ad.get("daily_budget") or 0) - (ad.get("daily_spent") or 0))
        ad["remaining_budget"] = remaining_budget

        return {
            "campaign": ad,
            "impression_id": imp_id,
            "cost": imp_result.get("cost", 0) or 0,
            "tip": imp_result.get("error", ""),
        }

    async def track_click(self, impression_id: int = None, campaign_id: int = None, searcher_tg_id: int = None) -> dict:
        """用户点击广告后调用：CPC才扣费，CPM不重复扣"""
        if not campaign_id and impression_id:
            async with get_db() as db:
                cur = await db.execute(
                    "SELECT campaign_id, searcher_tg_id FROM ad_impressions WHERE id=?",
                    (impression_id,)
                )
                r = await cur.fetchone()
                if r:
                    campaign_id = r["campaign_id"]
                    searcher_tg_id = searcher_tg_id or r["searcher_tg_id"]
        if not campaign_id:
            return {"success": False, "error": "缺少impression或campaign"}

        # 把之前那条曝光记录的is_click=1，再记录一次扣费（CPC）
        return await self.record_impression(
            campaign_id=campaign_id,
            searcher_tg_id=searcher_tg_id or 0,
            is_click=True,
            position=1,
        )

    async def get_advertiser_stats(self, tg_user_id: int) -> str:
        """广告主整体统计（格式化字符串，直接显示给用户）"""
        user = await wallet_manager.get_or_create_user(tg_user_id)
        camps = await self.list_campaigns(tg_user_id)
        total_imps = 0
        total_clicks = 0
        total_cost = 0.0
        active_c = 0
        for c in camps:
            s = await self.get_campaign_stats(c["id"])
            total_imps += s["total_impressions"] or 0
            total_clicks += s["total_clicks"] or 0
            total_cost += s["total_cost"] or 0
            if c.get("status") == "active":
                active_c += 1
        ctr = (total_clicks / total_imps * 100) if total_imps else 0
        balance = await wallet_manager.get_balance(tg_user_id)
        return (
            f"📈 广告主数据汇总\n"
            f"————————————————\n"
            f"投放中广告：{active_c} 个\n"
            f"历史广告数：{len(camps)} 个\n"
            f"总曝光量：{total_imps:,} 次\n"
            f"总点击量：{total_clicks:,} 次\n"
            f"整体CTR：{ctr:.2f}%\n"
            f"累计消耗：${total_cost:.4f} USDT\n"
            f"当前余额：${balance:.2f} USDT\n"
        )


# 全局实例
ad_manager = AdManager()
