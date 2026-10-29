import Foundation
import PDFKit
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("Uso: pdf_render <entrada.pdf> <salida.png> [ancho_max]\n", stderr)
    exit(1)
}

let inputPath = args[1]
let outputPath = args[2]
let maxWidth = args.count > 3 ? (Double(args[3]) ?? 2200.0) : 2200.0

guard let document = PDFDocument(url: URL(fileURLWithPath: inputPath)),
      let page = document.page(at: 0) else {
    fputs("No se pudo abrir el PDF\n", stderr)
    exit(2)
}

let bounds = page.bounds(for: .mediaBox)
guard bounds.width > 1, bounds.height > 1 else {
    fputs("Página PDF inválida\n", stderr)
    exit(3)
}

let scale = maxWidth / Double(bounds.width)
let pixelWidth = max(1, Int(Double(bounds.width) * scale))
let pixelHeight = max(1, Int(Double(bounds.height) * scale))

let colorSpace = CGColorSpaceCreateDeviceRGB()
guard let context = CGContext(
    data: nil,
    width: pixelWidth,
    height: pixelHeight,
    bitsPerComponent: 8,
    bytesPerRow: 0,
    space: colorSpace,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
) else {
    fputs("No se pudo crear el contexto de imagen\n", stderr)
    exit(4)
}

context.setFillColor(NSColor.white.cgColor)
context.fill(CGRect(x: 0, y: 0, width: pixelWidth, height: pixelHeight))
context.scaleBy(x: scale, y: scale)
page.draw(with: .mediaBox, to: context)

guard let cgImage = context.makeImage() else {
    fputs("No se pudo generar la imagen\n", stderr)
    exit(5)
}

let representation = NSBitmapImageRep(cgImage: cgImage)
guard let data = representation.representation(using: .png, properties: [:]) else {
    fputs("No se pudo codificar PNG\n", stderr)
    exit(6)
}

do {
    try data.write(to: URL(fileURLWithPath: outputPath))
} catch {
    fputs("No se pudo escribir el PNG: \(error)\n", stderr)
    exit(7)
}
