import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: path),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cgImage = bitmap.cgImage else {
    fputs("No se pudo cargar la imagen\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["es-ES", "en-US"]
request.minimumTextHeight = 0.005

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
    guard let observations = request.results else { exit(0) }
    for observation in observations {
        guard let candidate = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        let x = Int(box.origin.x * CGFloat(cgImage.width))
        let y = Int((1 - box.origin.y - box.size.height) * CGFloat(cgImage.height))
        let w = Int(box.size.width * CGFloat(cgImage.width))
        let h = Int(box.size.height * CGFloat(cgImage.height))
        print("\(x)\t\(y)\t\(w)\t\(h)\t\(String(format: "%.3f", candidate.confidence))\t\(candidate.string)")
    }
} catch {
    fputs("Error Vision: \(error)\n", stderr)
    exit(2)
}
