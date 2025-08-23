from krita import Krita

from .loomis_head_plugin import LoomisHeadPlugin

app = Krita.instance()
extension = LoomisHeadPlugin(app)
app.addExtension(extension)
