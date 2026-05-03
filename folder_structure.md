# Folder Structure

```text
Youtube automation/
|-- avatars/
|-- data/
|   `-- input/
|       `-- topics.csv
|-- legacy/
|-- runs/
|   `-- <job_id>/
|       |-- 00_input/
|       |   `-- job.json
|       |-- 01_script/
|       |   |-- raw.txt
|       |   `-- script.json
|       |-- 02_audio/
|       |   |-- *.wav
|       |   `-- audio_manifest.json
|       |-- 03_timeline/
|       |   `-- timeline.json
|       |-- 04_render/
|       |   |-- final.mp4
|       |   `-- render_plan.json
|       `-- status.json
|-- youtube-videos-download/
|   |-- urls.csv
|   `-- videos/
|       `-- *.mp4
|-- ytautomation/
|   |-- api/
|   |   |-- __init__.py
|   |   `-- main.py
|   |-- core/
|   |   |-- __init__.py
|   |   |-- errors.py
|   |   |-- io.py
|   |   |-- logging.py
|   |   |-- models.py
|   |   |-- moviepy_compat.py
|   |   |-- paths.py
|   |   `-- settings.py
|   |-- modules/
|   |   |-- __init__.py
|   |   |-- csv_ingest.py
|   |   |-- gameplay_selector.py
|   |   |-- llm_script_generator.py
|   |   |-- timeline_builder.py
|   |   |-- tts_cartesia.py
|   |   `-- video_renderer.py
|   |-- orchestrator/
|   |   |-- __init__.py
|   |   |-- csv_controller.py
|   |   `-- job_manager.py
|   |-- prompts/
|   |   `-- script_prompt.txt
|   |-- __init__.py
|   |-- cli.py
|   |-- pipeline.py
|   `-- README.md
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- run_api.ps1
`-- run_cli_examples.ps1
```
