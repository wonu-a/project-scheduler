<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ja">
<context>
    <name>CalendarDialog</name>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="146"/>
        <source>OK</source>
        <translation>決定</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="148"/>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="149"/>
        <source>Project calendar</source>
        <translation>プロジェクトカレンダー</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="150"/>
        <source>Project start date</source>
        <translation>プロジェクト開始日</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="151"/>
        <source>Working days</source>
        <translation>稼働日</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="152"/>
        <source>Holidays</source>
        <translation>休日</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="153"/>
        <source>Add</source>
        <translation>追加</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="154"/>
        <source>Remove</source>
        <translation>削除</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="160"/>
        <source>No holidays yet. Pick a date above and add it.</source>
        <translation>休日はまだありません。上で日付を選んで追加してください。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/calendar_dialog.py" line="212"/>
        <source>Edit calendar</source>
        <translation>カレンダーを編集</translation>
    </message>
</context>
<context>
    <name>Commands</name>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="31"/>
        <source>Add task “{0}”</source>
        <translation>タスク「{0}」を追加</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="72"/>
        <source>Edit task “{0}”</source>
        <translation>タスク「{0}」を編集</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="112"/>
        <source>Edit notes of “{0}”</source>
        <translation>「{0}」のメモを編集</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="146"/>
        <source>Delete task “{0}”</source>
        <translation>タスク「{0}」を削除</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="148"/>
        <source>Delete {0} tasks</source>
        <translation>{0} 件のタスクを削除</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="207"/>
        <source>Make “{0}” depend on “{1}”</source>
        <translation>「{0}」を「{1}」に依存させる</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="232"/>
        <source>Remove dependency of “{0}” on “{1}”</source>
        <translation>「{0}」の「{1}」への依存を削除</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="292"/>
        <source>Edit calendar</source>
        <translation>カレンダーを編集</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/commands.py" line="301"/>
        <source>Change start date</source>
        <translation>開始日を変更</translation>
    </message>
</context>
<context>
    <name>Errors</name>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="19"/>
        <source>The task name must not be empty.</source>
        <translation>タスク名を入力してください。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="21"/>
        <source>The duration must be a whole number from {0} to {1}.</source>
        <translation>期間は {0} から {1} までの整数で指定してください。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="25"/>
        <source>Task “{0}” cannot depend on itself.</source>
        <translation>タスク「{0}」は自分自身に依存できません。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="27"/>
        <source>Task {0} does not exist.</source>
        <translation>タスク {0} は存在しません。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="29"/>
        <source>“{0}” already depends on “{1}”.</source>
        <translation>「{0}」はすでに「{1}」に依存しています。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="33"/>
        <source> → </source>
        <translation> → </translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="35"/>
        <source>This dependency would create a cycle: {0}</source>
        <translation>この依存関係は循環を生じます: {0}</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="37"/>
        <source>Select at least one working day.</source>
        <translation>稼働日を 1 日以上選択してください。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="39"/>
        <source>The calendar contains an invalid weekday.</source>
        <translation>カレンダーに無効な曜日が含まれています。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="41"/>
        <source>The task no longer exists.</source>
        <translation>このタスクはもう存在しません。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="43"/>
        <source>Two tasks share the id {0}.</source>
        <translation>ID {0} が複数のタスクで重複しています。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="44"/>
        <source>The project data is inconsistent.</source>
        <translation>プロジェクトのデータに矛盾があります。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="50"/>
        <source>The file {0} was not found. Starting with an empty project.</source>
        <translation>ファイル {0} が見つかりません。空のプロジェクトで開始します。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="52"/>
        <source>The file {0} could not be read. A copy was kept as {1}. Starting with an empty project.</source>
        <translation>ファイル {0} を読み込めませんでした。コピーを {1} として保存しました。空のプロジェクトで開始します。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="56"/>
        <source>The file {0} could not be read. Starting with an empty project.</source>
        <translation>ファイル {0} を読み込めませんでした。空のプロジェクトで開始します。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="58"/>
        <source>The file {0} was saved by a newer version of Project Scheduler and cannot be opened.</source>
        <translation>ファイル {0} は新しいバージョンのプロジェクトスケジューラーで保存されているため、開けません。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="62"/>
        <source>The file {0} was upgraded from an older format. Save it to keep the new format.</source>
        <translation>ファイル {0} を古い形式から変換しました。新しい形式で残すには保存してください。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/errors.py" line="67"/>
        <source>The file {0} could not be saved: {1}</source>
        <translation>ファイル {0} を保存できませんでした: {1}</translation>
    </message>
</context>
<context>
    <name>MainWindow</name>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="339"/>
        <source>&amp;File</source>
        <translation>ファイル(&amp;F)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="340"/>
        <source>&amp;Edit</source>
        <translation>編集(&amp;E)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="341"/>
        <source>&amp;Project</source>
        <translation>プロジェクト(&amp;P)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="342"/>
        <source>&amp;View</source>
        <translation>表示(&amp;V)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="343"/>
        <source>Open &amp;recent</source>
        <translation>最近使ったファイル(&amp;R)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="344"/>
        <source>Load &amp;sample project</source>
        <translation>サンプルプロジェクトを読み込む(&amp;S)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="345"/>
        <source>&amp;Theme</source>
        <translation>テーマ(&amp;T)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="346"/>
        <source>&amp;Language</source>
        <translation>言語(&amp;L)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="348"/>
        <source>&amp;New project</source>
        <translation>新規プロジェクト(&amp;N)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="349"/>
        <source>&amp;Open…</source>
        <translation>開く(&amp;O)…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="350"/>
        <source>&amp;Save</source>
        <translation>保存(&amp;S)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="351"/>
        <source>Save &amp;as…</source>
        <translation>名前を付けて保存(&amp;A)…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="352"/>
        <source>&amp;Quit</source>
        <translation>終了(&amp;Q)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="353"/>
        <source>&amp;Undo</source>
        <translation>元に戻す(&amp;U)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="354"/>
        <source>&amp;Redo</source>
        <translation>やり直し(&amp;R)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="355"/>
        <source>&amp;Add task…</source>
        <translation>タスクを追加(&amp;A)…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="356"/>
        <source>&amp;Edit task…</source>
        <translation>タスクを編集(&amp;E)…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="357"/>
        <source>&amp;Delete</source>
        <translation>削除(&amp;D)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="358"/>
        <source>&amp;Calendar…</source>
        <translation>カレンダー(&amp;C)…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="360"/>
        <source>{0} tasks</source>
        <translation>{0} 件のタスク</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="361"/>
        <source>&amp;Light</source>
        <translation>ライト(&amp;L)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="362"/>
        <source>&amp;Dark</source>
        <translation>ダーク(&amp;D)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="363"/>
        <source>English</source>
        <translation>英語</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="363"/>
        <source>German</source>
        <translation>ドイツ語</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="363"/>
        <source>Japanese</source>
        <translation>日本語</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="367"/>
        <source>{0} ({1})</source>
        <translation>{0}（{1}）</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="368"/>
        <source>Toolbar</source>
        <translation>ツールバー</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="376"/>
        <location filename="../src/project_scheduler/ui/main_window.py" line="378"/>
        <location filename="../src/project_scheduler/ui/main_window.py" line="429"/>
        <source>Project Scheduler</source>
        <translation>プロジェクトスケジューラー</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="379"/>
        <source>Tasks</source>
        <translation>タスク</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="380"/>
        <source>Project finish</source>
        <translation>プロジェクト完了日</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="381"/>
        <source>Critical tasks</source>
        <translation>クリティカルタスク</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="382"/>
        <source>Filter tasks by name…</source>
        <translation>タスク名で絞り込み…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="383"/>
        <source>Show critical tasks only</source>
        <translation>クリティカルタスクのみ表示</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="384"/>
        <source>Critical</source>
        <translation>クリティカル</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="385"/>
        <source>Zero slack: any delay moves the project finish.</source>
        <translation>余裕ゼロ: 少しでも遅れるとプロジェクトの完了が遅れます。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="392"/>
        <location filename="../src/project_scheduler/ui/main_window.py" line="505"/>
        <source>Untitled</source>
        <translation>無題</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="396"/>
        <source>{0}[*] — Project Scheduler</source>
        <translation>{0}[*] — プロジェクトスケジューラー</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="404"/>
        <source>—</source>
        <translation>—</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="431"/>
        <source>OK</source>
        <translation>決定</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="453"/>
        <source>Unsaved changes</source>
        <translation>未保存の変更</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="454"/>
        <source>{0} has unsaved changes. Save them first?</source>
        <translation>{0} には未保存の変更があります。先に保存しますか?</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="470"/>
        <source>Loaded a sample project with {0} tasks.</source>
        <translation>{0} 件のタスクを含むサンプルプロジェクトを読み込みました。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="478"/>
        <source>Open project</source>
        <translation>プロジェクトを開く</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="478"/>
        <source>Schedules (*.schedule.json);;All files (*)</source>
        <translation>スケジュール (*.schedule.json);;すべてのファイル (*)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="507"/>
        <source>Save project</source>
        <translation>プロジェクトを保存</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="507"/>
        <source>Schedules (*.schedule.json)</source>
        <translation>スケジュール (*.schedule.json)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="526"/>
        <source>Saved {0}.</source>
        <translation>{0} を保存しました。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/main_window.py" line="533"/>
        <source>No recent files</source>
        <translation>最近使ったファイルはありません</translation>
    </message>
</context>
<context>
    <name>PredecessorListModel</name>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="245"/>
        <source>{0} · {1}</source>
        <translation>{0} · {1}</translation>
    </message>
</context>
<context>
    <name>TaskDialog</name>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="120"/>
        <source>OK</source>
        <translation>決定</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="122"/>
        <source>Edit task</source>
        <translation>タスクを編集</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="122"/>
        <source>New task</source>
        <translation>新しいタスク</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="125"/>
        <source>&amp;Name:</source>
        <translation>名前(&amp;N):</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="126"/>
        <source>&amp;Duration:</source>
        <translation>期間(&amp;D):</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="127"/>
        <source>N&amp;otes:</source>
        <translation>メモ(&amp;O):</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="128"/>
        <source>Optional notes about this task</source>
        <translation>このタスクに関するメモ（任意）</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="129"/>
        <source>&amp;Predecessors:</source>
        <translation>先行タスク(&amp;P):</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="130"/>
        <source> working days</source>
        <translation> 稼働日</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="131"/>
        <source>What needs to be done?</source>
        <translation>作業内容を入力</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="132"/>
        <source>Filter tasks…</source>
        <translation>タスクを絞り込み…</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="134"/>
        <source>No other tasks yet. Once the project has more tasks, you can choose predecessors here.</source>
        <translation>ほかのタスクはまだありません。タスクが増えると、ここで先行タスクを選択できます。</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_dialog.py" line="181"/>
        <source>Edit task “{0}”</source>
        <translation>タスク「{0}」を編集</translation>
    </message>
</context>
<context>
    <name>TaskTableModel</name>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="69"/>
        <source>, </source>
        <translation>、</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="70"/>
        <source>Critical</source>
        <translation>クリティカル</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="165"/>
        <source>ID</source>
        <translation>ID</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="166"/>
        <source>Name</source>
        <translation>名前</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="167"/>
        <source>Duration (days)</source>
        <translation>期間 (日)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="168"/>
        <source>Predecessors</source>
        <translation>先行タスク</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="169"/>
        <source>Start</source>
        <translation>開始</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="170"/>
        <source>Finish</source>
        <translation>終了</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="171"/>
        <source>Latest start</source>
        <translation>最遅開始</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="172"/>
        <source>Latest finish</source>
        <translation>最遅終了</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="173"/>
        <source>Slack (days)</source>
        <translation>余裕 (日)</translation>
    </message>
    <message>
        <location filename="../src/project_scheduler/ui/task_model.py" line="174"/>
        <source>Critical path</source>
        <translation>クリティカルパス</translation>
    </message>
</context>
</TS>
