// Rasteriza a 1a pagina de um PDF vetorial em PNG transparente, na escala pedida.
// uso: swift pdf_png.swift entrada.pdf saida.png escala
import Foundation
import PDFKit
import AppKit
let a = CommandLine.arguments
guard a.count >= 4, let doc = PDFDocument(url: URL(fileURLWithPath: a[1])), let page = doc.page(at: 0) else { exit(1) }
let escala = CGFloat(Double(a[3]) ?? 8)
let caixa = page.bounds(for: .mediaBox)
let w = Int(caixa.width * escala), h = Int(caixa.height * escala)
let cs = CGColorSpace(name: CGColorSpace.sRGB)!
guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: cs,
                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { exit(2) }
ctx.clear(CGRect(x: 0, y: 0, width: w, height: h))
ctx.scaleBy(x: escala, y: escala)
page.draw(with: .mediaBox, to: ctx)
let img = ctx.makeImage()!
let rep = NSBitmapImageRep(cgImage: img)
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[2]))
print("pagina \(caixa.width)x\(caixa.height) pt -> \(w)x\(h) px")
