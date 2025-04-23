import logging,os
import time
from config_manager import load_config, save_config
from novel_generator.chapter import generate_chapter_draft
from novel_generator.finalization import finalize_chapter
from novel_generator.common import call_with_retry
from utils import clear_file_content,save_string_to_txt,read_file
from novel_generator import (
    Novel_architecture_generate,
    Chapter_blueprint_generate,
    generate_chapter_draft,
    finalize_chapter,
    import_knowledge_file,
    clear_vector_store,
    enrich_chapter_text
)
class AutoNovelWriter:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.max_retries = 30
        self.retry_delay = 30  # 秒

    def _update_progress(self, chapter_num):
        """更新配置中的当前章节进度"""
        self.config["other_params"]["chapter_num"] = str(chapter_num)
        save_config(self.config, self.config_path)

    def _get_current_chapter(self):
        """获取当前应生成的章节号"""
        return int(self.config["other_params"].get("chapter_num", 1))

    def _get_total_chapters(self):
        """获取总章节数"""
        return int(self.config["other_params"].get("num_chapters", 240))

    def run(self):
        current_chapter = self._get_current_chapter()
        total_chapters = self._get_total_chapters()
        # self._generate_draft0()
        # self._generate_draft1()

        while current_chapter <= total_chapters:
            logging.info(f"开始生成第 {current_chapter} 章")

            # 生成草稿
            draft_success = call_with_retry(
                self._generate_draft,
                max_retries=self.max_retries,
                sleep_time=self.retry_delay,
                chapter_num=current_chapter
            )

            if not draft_success:
                logging.error(f"第 {current_chapter} 章生成失败，跳过")
                current_chapter += 1
                continue

            # 定稿处理
            finalize_success = call_with_retry(
                self._finalize_chapter,
                max_retries=self.max_retries,
                sleep_time=self.retry_delay,
                chapter_num=current_chapter
            )

            if finalize_success:
                logging.info(f"第 {current_chapter} 章处理完成")
                self._update_progress(current_chapter + 1)
                current_chapter += 1
            else:
                logging.error(f"第 {current_chapter} 章定稿失败，保留为草稿")
                current_chapter += 1
    def _generate_draft0(self):
        """包装章节生成函数"""
        params = self.config
        other_params = params["other_params"]
        llm_config = params["llm_configs"]["OpenAI"]
        try:
            logging.info("开始生成小说架构...")
            Novel_architecture_generate(
                interface_format="OpenAI",
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                llm_model=llm_config["model_name"],
                topic=other_params["topic"],
                genre=other_params["genre"],
                number_of_chapters=other_params["num_chapters"],
                word_number=int(other_params["word_number"]),
                filepath=other_params["filepath"],
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                timeout=llm_config["timeout"],
                user_guidance=other_params["user_guidance"]  # 添加内容指导参数
            )
            logging.info("✅ 小说架构生成完成。请在 'Novel Architecture' 标签页查看或编辑。")
        except Exception:
            logging.info("生成小说架构时出错")

    def _generate_draft1(self):
        """包装章节生成函数"""
        params = self.config
        other_params = params["other_params"]
        llm_config = params["llm_configs"]["OpenAI"]

        try:
            logging.info("开始生成章节蓝图...")
            Chapter_blueprint_generate(
                interface_format="OpenAI",
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                llm_model=llm_config["model_name"],
                number_of_chapters=other_params["num_chapters"],
                filepath=other_params["filepath"],
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                timeout=llm_config["timeout"],
                user_guidance=other_params["user_guidance"]  # 新增参数
            )
            logging.info("✅ 章节蓝图生成完成。请在 'Chapter Blueprint' 标签页查看或编辑。")
        except Exception:
            logging.info("生成章节蓝图时出错")

    def _generate_draft(self, chapter_num):
        """包装章节生成函数"""
        params = self.config
        other_params = params["other_params"]
        llm_config = params["llm_configs"]["OpenAI"]
        embedding_config = params["embedding_configs"]["SiliconFlow"]

        try:
            generate_chapter_draft(
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                model_name=llm_config["model_name"],
                filepath=other_params["filepath"],
                novel_number=chapter_num,
                word_number=int(other_params["word_number"]),
                temperature=llm_config["temperature"],
                user_guidance=other_params["user_guidance"],
                characters_involved=other_params["characters_involved"],
                key_items=other_params["key_items"],
                scene_location=other_params["scene_location"],
                time_constraint=other_params["time_constraint"],
                embedding_api_key=embedding_config["api_key"],
                embedding_url=embedding_config["base_url"],
                embedding_interface_format="SiliconFlow",
                embedding_model_name=embedding_config["model_name"],
                embedding_retrieval_k=int(embedding_config["retrieval_k"]),
                interface_format="OpenAI",
                max_tokens=llm_config["max_tokens"],
                timeout=llm_config["timeout"]
            )
            return True
        except Exception as e:
            logging.error(f"生成异常: {str(e)}")
            return False

    def _finalize_chapter(self, chapter_num):
        """包装定稿函数"""
        params = self.config
        other_params = params["other_params"]
        llm_config = params["llm_configs"]["OpenAI"]
        embedding_config = params["embedding_configs"]["SiliconFlow"]
        filepath = "./filepath"
        chapters_dir = os.path.join(filepath, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")
        chapter_text = read_file(chapter_file).strip()

        try:
            if len(chapter_text) < 1 * int(other_params["word_number"]):
                logging.info("正在扩写章节内容...")
                enriched = enrich_chapter_text(
                    chapter_text=chapter_text,
                    word_number=int(other_params["word_number"]),
                    api_key=llm_config["api_key"],
                    base_url=llm_config["base_url"],
                    model_name=llm_config["model_name"],
                    temperature=llm_config["temperature"],
                    interface_format="OpenAI",
                    max_tokens=llm_config["max_tokens"],
                    timeout=llm_config["timeout"]
                )
                logging.info("扩写章节内容完成")
                edited_text = enriched
                clear_file_content(chapter_file)
                save_string_to_txt(edited_text, chapter_file)
            logging.info("正在定稿。。")
            finalize_chapter(
                novel_number=chapter_num,
                word_number=int(other_params["word_number"]),
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                model_name=llm_config["model_name"],
                temperature=llm_config["temperature"],
                filepath=other_params["filepath"],
                embedding_api_key=embedding_config["api_key"],
                embedding_url=embedding_config["base_url"],
                embedding_interface_format="SiliconFlow",
                embedding_model_name=embedding_config["model_name"],
                interface_format="OpenAI",
                max_tokens=llm_config["max_tokens"],
                timeout=llm_config["timeout"]
            )
            logging.info("定稿完成")
            return True
        except Exception as e:
            logging.error(f"定稿异常: {str(e)}")
            return False

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    writer = AutoNovelWriter()
    writer.run()