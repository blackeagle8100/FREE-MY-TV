#!/usr/bin/env python3

"""Fullscreen startscherm voor de tv-computer.

Het startscherm blijft tijdens een browsersessie actief. Een klik op een
zender start TVBROWSER als een apart proces en verbergt dit venster. Zodra
TVBROWSER stopt (normaal of door een fout), verschijnt het startscherm weer.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
import subprocess
from PyQt6.QtCore import QProcess, QSize, QTimer, Qt
from PyQt6.QtGui import QCloseEvent, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QWidget,
)


PAGE_SIZE = 9
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


def resolve_app_directory() -> Path:
    """Zoek de map met scripts en afbeeldingen."""

    configured_path = os.environ.get("TV_APP_DIR")
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    script_directory = Path(__file__).resolve().parent
    candidates = (
        script_directory,
        Path.home() / "Documents" / "TV",
        Path.home() / "TV",
    )

    for candidate in candidates:
        if (candidate / "icons").is_dir():
            return candidate

    return script_directory


APP_DIRECTORY = resolve_app_directory()


class MainWindow(QMainWindow):
    def __init__(self, screen_width: int, screen_height: int) -> None:
        super().__init__()
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.setWindowTitle("TV and music")

        self.images: list[Path] = []
        self.current_batch_start = 0
        self.browser_process: QProcess | None = None
        self.background_pixmap = QPixmap()

        self.create_widgets()
        self.load_images()

    def load_images(self) -> None:
        folder_path = APP_DIRECTORY / "icons"

        if folder_path.is_dir():
            self.images = sorted(
                path
                for path in folder_path.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
        else:
            self.images = []
            print(f"Iconenmap niet gevonden: {folder_path}", file=sys.stderr)

        self.current_batch_start = 0
        self.show_current_batch()

    @staticmethod
    def program_name(image_path: Path) -> str:
        """Haal de programmanaam uit bijvoorbeeld ``01-vrt.png``."""

        name = image_path.stem
        if "-" in name:
            name = name.split("-", 1)[1]
        return name.strip().casefold()

    def find_browser_script(self) -> Path | None:
        configured_path = os.environ.get("TV_BROWSER_SCRIPT")
        if configured_path:
            candidate = Path(configured_path).expanduser()
            if candidate.is_file():
                return candidate.resolve()

        script_directory = Path(__file__).resolve().parent
        directories = tuple(dict.fromkeys((APP_DIRECTORY, script_directory)))

        for directory in directories:
            candidate = directory / "TVBROWSER.py"
            if candidate.is_file():
                return candidate.resolve()

        # Ondersteunt ook downloadnamen zoals TVBROWSER(3).py. Kies het
        # hoogste versienummer, zodat een oudere kopie niet per ongeluk start.
        versioned_scripts: list[tuple[int, Path]] = []
        other_scripts: list[Path] = []
        for directory in directories:
            for candidate in directory.glob("TVBROWSER*.py"):
                if not candidate.is_file():
                    continue

                match = re.fullmatch(
                    r"TVBROWSER\((\d+)\)\.py", candidate.name, re.IGNORECASE
                )
                if match:
                    versioned_scripts.append((int(match.group(1)), candidate))
                else:
                    other_scripts.append(candidate)

        if versioned_scripts:
            newest = max(versioned_scripts, key=lambda item: item[0])[1]
            return newest.resolve()
        if other_scripts:
            return sorted(other_scripts)[-1].resolve()

        return None

    def goto(self, image_path: Path) -> None:
        """Start de browser zonder het tv-startscherm af te sluiten."""

        if self.browser_process is not None:
            return

        browser_script = self.find_browser_script()
        if browser_script is None:
            QMessageBox.critical(
                self,
                "TV-browser niet gevonden",
                "TVBROWSER.py staat niet naast TV.py en werd ook niet in de "
                "TV-map gevonden.",
            )
            return

        program = self.program_name(image_path)
        if not program:
            QMessageBox.warning(
                self,
                "Ongeldig pictogram",
                f"Geen programmanaam gevonden in {image_path.name}.",
            )
            return

        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments([str(browser_script), program])
        process.setWorkingDirectory(str(APP_DIRECTORY))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedChannels)
        process.started.connect(self.browser_started)
        process.finished.connect(self.browser_finished)
        process.errorOccurred.connect(self.browser_error)

        self.browser_process = process
        self.setEnabled(False)
        print(f"TVBROWSER starten voor: {program}")
        process.start()

    def browser_started(self) -> None:
        # Hide sluit het venster niet: de Qt-eventloop en TV.py blijven actief.
        self.hide()

    def browser_finished(
        self, exit_code: int, exit_status: QProcess.ExitStatus
    ) -> None:
        if exit_code != 0 or exit_status == QProcess.ExitStatus.CrashExit:
            print(
                f"TVBROWSER stopte met code {exit_code} ({exit_status.name}).",
                file=sys.stderr,
            )

        self.finish_browser_session()

    def browser_error(self, error: QProcess.ProcessError) -> None:
        process = self.browser_process
        message = process.errorString() if process is not None else str(error)
        print(f"TVBROWSER kon niet worden gestart: {message}", file=sys.stderr)

        if error == QProcess.ProcessError.FailedToStart:
            self.finish_browser_session()
            QMessageBox.critical(
                self,
                "TV-browser kon niet starten",
                message,
            )

    def finish_browser_session(self) -> None:
        process = self.browser_process
        self.browser_process = None

        if process is not None:
            process.deleteLater()

        self.setEnabled(True)
        self.showFullScreen()
        QTimer.singleShot(100, self.activate_home_screen)

    def activate_home_screen(self) -> None:
        self.raise_()
        self.activateWindow()

    def show_current_batch(self) -> None:
        image_height = 200
        image_width = 200

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index in range(PAGE_SIZE):
            image_index = self.current_batch_start + index
            if image_index >= len(self.images):
                break

            image_path = self.images[image_index]
            image_label = QLabel(self)
            pixmap = QPixmap(str(image_path)).scaled(
                image_width,
                image_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setCursor(Qt.CursorShape.PointingHandCursor)
            image_label.mousePressEvent = (
                lambda event, path=image_path: self.goto(path)
            )
            self.grid_layout.addWidget(image_label, index // 3 , index % 3)

        self.back_button.setVisible(self.current_batch_start > 0)
        self.forward_button.setVisible(
            self.current_batch_start + PAGE_SIZE < len(self.images)
        )

    def show_previous_batch(self, event=None) -> None:
        if self.current_batch_start > 0:
            self.current_batch_start = max(
                0, self.current_batch_start - PAGE_SIZE
            )
            self.show_current_batch()

    def show_next_batch(self, event=None) -> None:
        if self.current_batch_start + PAGE_SIZE < len(self.images):
            self.current_batch_start += PAGE_SIZE
            self.show_current_batch()

    def set_background(self) -> None:
        background_path = APP_DIRECTORY / "background.png"
        if not background_path.is_file():
            print(
                f"Achtergrondbestand bestaat niet: {background_path}",
                file=sys.stderr,
            )
            self.setStyleSheet("QMainWindow { background-color: black; }")
            return

        self.background_pixmap = QPixmap(str(background_path))
        self.background_label = QLabel(self)
        self.background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.background_label.lower()
        self.update_background()

    def update_background(self) -> None:
        if self.background_pixmap.isNull() or not hasattr(
            self, "background_label"
        ):
            return

        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            size.setWidth(self.screen_width)
            size.setHeight(self.screen_height)

        scaled = self.background_pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.background_label.setGeometry(self.rect())
        self.background_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_background()

    def create_widgets(self) -> None:
        self.set_background()

        power_button_size = 80
        power_icon_path = Path(__file__).resolve().parent / "poweroff.png"

        self.power_button = QPushButton(self)
        self.power_button.setFixedSize(power_button_size, power_button_size)
        self.power_button.setIconSize(QSize(64, 64))
        self.power_button.setFlat(True)
        self.power_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.power_button.setToolTip("Afsluiten")
        self.power_button.setAccessibleName("Afsluiten")
        self.power_button.clicked.connect(self.afsluiten)

        if power_icon_path.is_file():
            self.power_button.setIcon(QIcon(str(power_icon_path)))
        else:
            print(
                f"Powericoon niet gevonden: {power_icon_path}",
                file=sys.stderr,
            )
            self.power_button.setText("⏻")

        self.power_button.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 40);
                border-radius: 40px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 80);
            }
            """
        )

        self.back_button = QLabel(self)
        self.back_button.setMinimumHeight(300)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_arrow(self.back_button, "arrowleft.png")
        self.back_button.mousePressEvent = self.show_previous_batch

        self.forward_button = QLabel(self)
        self.forward_button.setMinimumHeight(300)
        self.forward_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_arrow(self.forward_button, "arrowright.png")
        self.forward_button.mousePressEvent = self.show_next_batch

        self.grid_layout = QGridLayout()
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)

        content_layout = QGridLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(0)
        content_layout.setVerticalSpacing(0)

        # De zijkolommen blijven even breed, ook wanneer een pijl verborgen is.
        # Zo blijft het zenderrooster exact in het horizontale midden staan.
        content_layout.setColumnMinimumWidth(0, 200)
        content_layout.setColumnMinimumWidth(2, 200)
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 0)
        content_layout.setColumnStretch(2, 1)

        content_layout.addWidget(
            self.back_button,
            0,
            0,
            alignment=(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            ),
        )
        content_layout.addLayout(
            self.grid_layout,
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        content_layout.addWidget(
            self.forward_button,
            0,
            2,
            alignment=(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            ),
        )

        main_layout = QGridLayout()
        main_layout.setContentsMargins(0, 30, 0, 30)
        main_layout.setHorizontalSpacing(0)
        main_layout.setVerticalSpacing(0)

        # De lege onderste rij is even hoog als de rij met de powerknop.
        # Daardoor ligt het midden van de zendergrid ook verticaal exact in
        # het midden van het scherm.
        main_layout.setRowMinimumHeight(0, power_button_size)
        main_layout.setRowStretch(1, 1)
        main_layout.setRowMinimumHeight(2, power_button_size)

        main_layout.addWidget(
            self.power_button,
            0,
            0,
            alignment=(
                Qt.AlignmentFlag.AlignTop
                | Qt.AlignmentFlag.AlignHCenter
            ),
        )
        main_layout.addLayout(content_layout, 1, 0)

        central_widget = QWidget(self)
        central_widget.setStyleSheet("background: transparent;")
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def afsluiten(self):
        subprocess.call("poweroff")


    @staticmethod
    def set_arrow(label: QLabel, filename: str) -> None:
        arrowwith = 200
        arrowheight = 500
        path = APP_DIRECTORY / "btn" / filename
        if not path.is_file():
            print(f"Pijl niet gevonden: {path}", file=sys.stderr)
            label.setFixedWidth(arrowwith)
            return

        pixmap = QPixmap(str(path)).scaled(
            arrowwith,
            arrowheight,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedWidth(arrowwith)

    def closeEvent(self, event: QCloseEvent) -> None:
        process = self.browser_process
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.terminate()
            if not process.waitForFinished(3000):
                process.kill()
                process.waitForFinished(1000)

        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    if screen is None:
        print("Geen beeldscherm gevonden.", file=sys.stderr)
        return 1

    geometry = screen.geometry()
    print(f"Schermgrootte: {geometry.width()} x {geometry.height()}")
    print(f"Device pixel ratio: {screen.devicePixelRatio()}")
    print(f"TV-map: {APP_DIRECTORY}")

    window = MainWindow(geometry.width(), geometry.height())
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
